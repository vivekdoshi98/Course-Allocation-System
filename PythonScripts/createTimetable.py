import xlsxwriter
import psycopg2

conn = psycopg2.connect(
   database="courses", 
   user='<<ENTER USERNAME>>', 
   password='<<ENTER PASSWORD>>', 
   host='<<ENTER HOST DETAILS>>', 
   port= '<<ENTER PORT>>'
)
conn.autocommit = False
cursor = conn.cursor()

#schema names - change these variables as per schema name changes in db
courseAllocationSchema='course_allocation'
timetableSchema='time_table'

#xls object
workbook = xlsxwriter.Workbook('timetable.xlsx')
worksheet = workbook.add_worksheet()
merge_format = workbook.add_format({
    'bold': 1,
    'border': 1,
    'align': 'center',
    'valign': 'vcenter'})
worksheet.write('A1', 'Time',merge_format)
worksheet.write('B1', 'Batch',merge_format)

#helper arrays
dayList=['MON','TUE','WED','THU','FRI']
xlCols=['A','B','C','D','E','F','G','H','I','J','K','L','M','N',
'O','P','Q','R','S','T','U','V','W','X','Y','Z','AA','AB','AC',
'AD','AE','AF','AG','AH','AI','AJ','AK','AL','AM','AN','AO','AP',
'AQ','AR','AS','AT','AU','AV','AW','AX','AY','AZ','BA','BB','BC',
'BD','BE','BF','BG','BH','BI','BJ','BK','BL','BM','BN','BO','BP',
'BQ','BR','BS','BT','BU','BV','BW','BX','BY','BZ']


#getting hours from time table
cursor.execute("select distinct hour from "+timetableSchema+".timetable order by hour")
hourList = cursor.fetchall()
hourList = [x[0] for x in hourList] #for single column it is returning list so converting it to 1D array

#getting hours from time table
cursor.execute("select programname from "+courseAllocationSchema+".programs")
progList = cursor.fetchall()
progList = [x[0] for x in progList] #for single column it is returning list so converting it to 1D array

##storing data in data structure
hourMap={}
for hl in hourList:
   dayMap={}
   for dl in dayList:
      #get slotno at hour hl and day dl
      query="select slotno from "+timetableSchema+".timetable where hour='"+hl+"' and day='"+dl+"'"
      cursor.execute(query)
      slotno=cursor.fetchone()
      slotno=slotno[0]

      ##getting slotdetails based on slotno
      cursor.execute("""
      (select p.programname,o.semester,s.courseno,c.coursename,c.credit,r.roomno,r.section,f.shortname 
      from """+timetableSchema+""".slotassigned s 
      join """+timetableSchema+""".roomassigned r 
      on s.courseno=r.courseno 
      join """+courseAllocationSchema+""".courses c  
      on r.courseno=c.courseno 
      join """+courseAllocationSchema+""".facultyassigned f 
      on f.courseno=c.courseno and r.section=f.section 
      join """+courseAllocationSchema+""".offer o  
      on o.courseno=c.courseno 
      join """+courseAllocationSchema+""".programs p 
      on p.programid=o.programid 
      where s.slotno='"""+slotno+"""') 
      union 
      (select p1.programname,o1.semester,s1.courseno,c1.coursename,c1.credit,r1.roomno,r1.section,f1.shortname 
      from """+timetableSchema+""".slotassigned s1 
      join """+timetableSchema+""".roomassigned r1 
      on s1.courseno=r1.courseno 
      join """+courseAllocationSchema+""".courses c1 
      on r1.courseno=c1.courseno 
      join """+courseAllocationSchema+""".facultyassigned f1 
      on f1.courseno=c1.courseno and r1.section=f1.section
      join """+courseAllocationSchema+""".openfor o1 
      on o1.courseno=c1.courseno 
      join """+courseAllocationSchema+""".programs p1 
      on p1.programid=o1.programid 
      where s1.slotno='"""+slotno+"""') 
      order by programname,semester,section
      """)

      slotRows=cursor.fetchall()
      slotMap={} ## map of prog,sem map
      for p in progList:
         slotMap[p]={}
      for row in slotRows:
         prog=row[0]
         sem=row[1]
         courseDet=[]
         for i in range(2,8):
            courseDet.append(row[i])

         semMap={}## map of sem,course details list
         if prog in slotMap:
            semMap=slotMap.get(prog)
         if sem in semMap:
            l=semMap.get(sem)
         else:
            l=[]
         l.append(courseDet)
         semMap[sem]=l
         slotMap[prog]=semMap
      dayMap[dl]=slotMap
   hourMap[hl]=dayMap

# ##Printing data
# for hm in hourMap:
#    print("Hour: "+hm)
#    dayM=hourMap.get(hm)
#    for dm in dayM:
#       print("day: "+dm)
#       sld=dayM.get(dm)
#       for r in sld:
#          print('Course: '+r)
#          d=sld.get(r)
#          for d1 in d:
#             print('Sem: '+str(d1))
#             print(d.get(d1))


##writing in xls

xlColInd=3
xlRowInd=3
tempRowPos=xlRowInd
tempColPos=xlColInd

hourHeaderRowIndex=3
progHeaderRowIndex=3

hourMergeSize={}
for hm in hourList:
   hourMergeSize[hm]=1

for hm in hourMap:
   ##getting merge size of hour and each prog
   progMergeSize={}
   for p in progList:
      progMergeSize[p]=1
      #print("prog: "+p+" "+str(progMergeSize[p]))
   maxHourMergeSize=0
   dayMap=hourMap.get(hm) # day map

   for dm in dayMap:
      progMap=dayMap.get(dm) # prog map of a day
      for pm in progMap:
         semMap=progMap.get(pm) # sem map of a prog
         courseCount=0
         for sm in semMap:
            courseList=semMap.get(sm) # course list of a sem
            courseCount+=len(courseList)
         progMergeSize[pm]=max(progMergeSize[pm],courseCount)
   
   # for p in progMergeSize:
   #    print("newprog: "+p+" "+str(progMergeSize[p]))
   
   for pms in progMergeSize:
      maxHourMergeSize+=progMergeSize.get(pms)
      if progMergeSize.get(pms)==1 :
         worksheet.write('B'+str(progHeaderRowIndex),pms,merge_format)
         progHeaderRowIndex=progHeaderRowIndex+1
      else:
         worksheet.merge_range('B'+str(progHeaderRowIndex)+':B'+str(progHeaderRowIndex+progMergeSize.get(pms)-1), pms, merge_format)
         progHeaderRowIndex+=progMergeSize.get(pms)

   xlColInd=3
   for dm in dayMap:
      progMap=dayMap.get(dm) # prog map of a day
      tempRowPos=xlRowInd
      for pm in progMap:
         ##print("Day -- "+dm)
         ##print("ROWNUM--"+str(tempRowPos)+"   PROG"+pm+"--- "+str(progMap.get(pm))+" size--- "+str(len(progMap.get(pm))))
         startRow=tempRowPos
         if len(progMap.get(pm)) != 0:
            semMap=progMap.get(pm)
            for sm in semMap:
               courseDet=semMap[sm]
               for cl in courseDet:
                  tempColPos=xlColInd
                  worksheet.write(xlCols[tempColPos]+str(tempRowPos),'Sem '+str(sm))
                  tempColPos+=1
                  for c in cl:
                     #write to xl   
                     worksheet.write(xlCols[tempColPos]+str(tempRowPos),str(c))
                     tempColPos+=1
                  tempRowPos+=1 
             
         ##print("NOW ROW- "+str(tempRowPos)+" Max rows- "+str(progMergeSize[pm])+" startRow- "+str(startRow))
         tempRowPos+=progMergeSize[pm]-(tempRowPos-startRow)
      xlColInd=tempColPos+1
   
   worksheet.merge_range('A'+str(hourHeaderRowIndex)+':A'+str(hourHeaderRowIndex+maxHourMergeSize-1), hm, merge_format)
   hourMergeSize[hm]=maxHourMergeSize
   hourHeaderRowIndex+=maxHourMergeSize+2
   xlRowInd=hourHeaderRowIndex
   progHeaderRowIndex+=2

dayHeaderIndex=3
for d in dayList:
   worksheet.merge_range(xlCols[dayHeaderIndex]+"1:"+xlCols[dayHeaderIndex+6]+"1", d, merge_format)
   dayHeaderIndex+=8


workbook.close()
conn.close()