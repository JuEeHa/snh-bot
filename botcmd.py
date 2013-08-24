import time
import threading

concmd=['/q']

activitylines=3 #how many lines
activitytime=5*60 #in how many seconds consititues activity
watchnicks=['shikhin','shikhin_'] #Who this bot will watch, all presumed to be same person for now
worktimes=[((0,0),(23,59))] #Work times in a ((starthour,startmin),(endhour,endmin)) format NOTE: times in UTC

quitflag=[False] #ugly hack but otherwise /q would not work
quitflaglock=threading.Lock()
activity=[] #list of message send times, if over activitylines in activitytime, reduce point
activitylock=threading.Lock()
points=[0]
pointslock=threading.Lock()
todo=[]
todolock=threading.Lock()

IRC=[None,'#osdev-offtopic'] # Channel object and irc channel

def stillrunnig():
	quitflaglock.acquire()
	t=quitflag[0]
	quitflaglock.release()
	return not t

def isworktime():
	r=False
	curtime=time.gmtime()
	for start,end in worktimes:
		if (start[0]<curtime.tm_hour or (start[0]==curtime.tm_hour and start[1]<=curtime.tm_min)) and (end[0]>curtime.tm_hour or (end[0]==curtime.tm_hour and end[1]>=curtime.tm_min)):
			r=True
			break
	return r

#Handle reseting points on specified time and updating activity queue
class Update(threading.Thread):
	def run(self):
		while stillrunnig():
			if isworktime():
				activitylock.acquire()
				for i in activity:
					if time.time()>=i+activitytime:
						del i
				if len(activity)>activitylines:
					pointslock.acquire()
					points[0]-=1
					while len(activity)>0:
						activity.pop()
					pointslock.release()
					
					todolock.acquire()
					if len(todo)>0:
						t=[(lambda x: x[1])(i) for i in reduce((lambda x,y: x+[y] if len(x)<5 else x[1:]+[y]),[[]]+todo)]
						t.reverse()
						IRC[0].send('PRIVMSG %s :You have stuff to do: %s'%(IRC[1],'; '.join(t)))
					todolock.release()
				activitylock.release()
			time.sleep(0.1)
def parse((line,irc)):
	if not IRC[0]:
		IRC[0]=irc
		Update().start()
	
	line=line.split(' ')
	nick=line[0].split('!')[0][1:]
	chan=line[2] if line[2][0]=='#' else nick
	
	if line[1]=='PRIVMSG':
		if line[3]==':snh-bot:' and line[4]=='points':
			pointslock.acquire()
			irc.send('PRIVMSG %s :%s'%(chan,str(points[0])))
			pointslock.release()
		elif line[3]==':snh-bot:' and line[4]=='todo-add':
			if len(line)<7:
				irc.send('PRIVMSG %s :Usage: snh-bot: todo-add PRIORITY TODO'%chan)
			else:
				run=True
				try:
					prio=int(line[5])
				except ValueError:
					irc.send('PRIVMSG %s :PRIORITY must be number'%chan)
					run=False
				if run:
					todolock.acquire()
					todo.append((prio,' '.join(line[6:])))
					todo.sort()
					todolock.release()
		elif line[3]==':snh-bot:' and line[4]=='todo-list':
			todolock.acquire()
			t=[(lambda x: x[1])(i) for i in reduce((lambda x,y: x+[y] if len(x)<5 else x[1:]+[y]),[[]]+todo)]
			t.reverse()
			irc.send('PRIVMSG %s :%s'%(chan,'; '.join(t)))
			todolock.release()
		elif nick in watchnicks and isworktime():
			activitylock.acquire()
			activity.append(time.time())
			activitylock.release()

def execcmd(s):
	if s[0]=='/q':
		quitflaglock.acquire()
		quitflag[0]=True
		quitflaglock.release()
