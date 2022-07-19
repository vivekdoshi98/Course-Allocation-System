import psycopg2

courseAllocationSchema='course_allocation'
timetableSchema='time_table'

##constraints functions
##Constraint 1 : Faculty should not be assigned more than 3 courses in a term/semester
def checkCourseAssignedCount(dbObj,fileObj):
    fileObj.write('\nConstraint 1 : Faculty should not be assigned more than 2 courses in a term/semester\n')
    terms=['A','W','N']
    flag=True
    for term in terms:
        query="select distinct f.shortname, count(o.courseno) as coursecount from "+courseAllocationSchema+".facultyassigned f join "+courseAllocationSchema+".offer o on f.courseno=o.courseno where o.term='"+term+"' group by f.shortname having count(o.courseno)>=3 order by coursecount"
        dbObj.execute(query)
        result=dbObj.fetchall()
        if len(result)>0:
            flag=False
            fileObj.write('\n---FAILED FOR TERM '+term+'---\n')
            fileObj.write('RESULT\n')
            for l in result:
                fileObj.write('Prof: '+l[0]+' Course Count: '+str(l[1])+'\n')
    if flag==True:
        fileObj.write('\n---PASSED---\n')

##Constraint 2 : Faculty should not have consecutive lectures
def checkConsecutiveLectures(dbObj,fileObj):
    fileObj.write('\nConstraint 2 : Faculty should not have consecutive lectures\n')
    dbObj.execute('select distinct day from '+timetableSchema+'.timetable')
    dayList=dbObj.fetchall()
    dayList = [x[0] for x in dayList] #for single column it is returning list so converting it to 1D array
    flag=True
    for dl in dayList:
        dbObj.execute("select hour from "+timetableSchema+".timetable where day='"+dl+"'")
        hourList = dbObj.fetchall() #getting hours from time table
        hourList = [x[0] for x in hourList] #for single column it is returning list so converting it to 1D array
        for i in range (0,len(hourList)-1):
            #print("checking day "+dl+" hour "+hourList[i]+" - "+hourList[i+1])
            dbObj.execute("""
            select a.shortname from
            (select distinct f.shortname
            from """+timetableSchema+""".timetable t
            join """+timetableSchema+""".slotassigned s
            on t.slotno=s.slotno
            join """+courseAllocationSchema+""".facultyassigned f
            on f.courseno=s.courseno
            where t.hour='"""+hourList[i]+"""' and t.day='"""+dl+"""') a 
            join 
            (select distinct f.shortname
            from """+timetableSchema+""".timetable t
            join """+timetableSchema+""".slotassigned s
            on t.slotno=s.slotno
            join """+courseAllocationSchema+""".facultyassigned f
            on f.courseno=s.courseno
            where t.hour='"""+hourList[i+1]+"""' and t.day='"""+dl+"""') b
            on a.shortname=b.shortname""")
            result=dbObj.fetchall()
            ##print("checking day "+dl+" hour "+hourList[i]+" - "+hourList[i+1])
            ##print(str(result)+"\n")
            if len(result)>0:
                if(len(result)==1):
                    if(result[0][0]=='TBD' or result[0][0]=='TBD2'):
                        continue
                flag=False
                fileObj.write('\n---FAILED FOR DAY: '+dl+'  HOUR: '+hourList[i]+" - "+hourList[i+1]+'---\n')
                fileObj.write('RESULT\n')
                for l in result:
                    fileObj.write('Prof: '+l[0]+'\n')
    if flag==True:
        fileObj.write('\n---PASSED---\n')


##Constraint 3 : No clashing of lectures for faculty - Slots should be assigned such that only 1 faculty teaches in 1 slot
def checkClashingLectures(dbObj,fileObj):
    fileObj.write('\nConstraint 3 : No clashing of lectures for faculty\n')
    dbObj.execute('''
        select s.slotno,f.shortname,count(s.courseno) from '''+timetableSchema+'''.slotassigned s
        join '''+courseAllocationSchema+'''.facultyassigned f
        on s.courseno=f.courseno
        group by f.shortname,s.slotno
        having count(s.courseno)>1
        order by s.slotno''')
    result =dbObj.fetchall()
    if len(result)>0:
        fileObj.write('\n---FAILED---\n')
        fileObj.write('RESULT\n')
        for l in result:
            fileObj.write('Prof: '+l[1]+' - Slot: '+l[0]+' - Course Count: '+str(l[2])+'\n')
    else:
        fileObj.write('\n---PASSED---\n')


##Constraint 4 : No clashing of rooms in any slots
def checkClashingRooms(dbObj,fileObj):
    fileObj.write('\nConstraint 4 : No clashing of rooms in any slot\n')
    dbObj.execute('''
        select s.slotno,r.roomno,count(s.courseno)
        from '''+timetableSchema+'''.slotassigned s 
        join '''+timetableSchema+'''.roomassigned r 
        on s.courseno=r.courseno
        group by r.roomno,s.slotno
        having count(s.courseno)>1
        order by s.slotno''')
    result =dbObj.fetchall()
    if len(result)>0:
        fileObj.write('\n---FAILED---\n')
        fileObj.write('RESULT\n')
        for l in result:
            fileObj.write('Room: '+l[1]+' - Slot: '+l[0]+' - Course Count: '+str(l[2])+'\n')
    else:
        fileObj.write('\n---PASSED---\n')



##establishing the db connection
conn = psycopg2.connect(
   database="courses", 
   user='<<ENTER USERNAME>>', 
   password='<<ENTER PASSWORD>>', 
   host='<<ENTER HOST DETAILS>>', 
   port= '<<ENTER PORT>>'
)
conn.autocommit = False
cursor = conn.cursor()

##txt file to write constraint output
f=open("constraintsLog.txt","w")
f.write('CONTRAINTS CHECK:-\n')

##calling all constraint functions
checkCourseAssignedCount(cursor,f)
checkConsecutiveLectures(cursor,f)
checkClashingLectures(cursor,f)
checkClashingRooms(cursor,f)




f.close()
conn.close()