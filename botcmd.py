import time
import threading

concmd=['/q']

activitylines=3 #how many lines
activitytime=5*60 #in how many seconds consititues activity
watchnicks=['shikhin','shikhin_','shikhin__','shikhout','shikherr','draumr','idraumr'] #Who this bot will watch, all presumed to be same person for now
worktimes=[] #Work times in a ((starthour,startmin),(endhour,endmin)) format NOTE: times in UTC
timeslock=threading.Lock()

quitflag=[False] #ugly hack but otherwise /q would not work
quitflaglock=threading.Lock()
activity=[] #list of message send times, if over activitylines in activitytime, reduce point
activitylock=threading.Lock()
points=[0]
pointslock=threading.Lock()
todo=[]
todolock=threading.Lock()

IRC=[None,'#shikhin-needs-help'] # Channel object and irc channel

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
		if line[3]==':snh-bot:' and line[4]=='reset-points':
			pointslock.acquire()
			points[0]=0
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
		elif line[3]==':snh-bot:' and line[4]=='todo-completed':
			if len(line)<6:
				irc.send('PRIVMSG %s :Usage: snh-bot: todo-completed TODO'%chan)
			else:
				todolock.acquire()
				t=filter((lambda x:x[0][1]==' '.join(line[5:])),zip(todo,range(len(todo))))
				if len(t)>0:
					pointslock.acquire()
					points[0]+=1
					pointslock.release()
					for i,j in t:
						del todo[j]
				else:
					irc.send('PRIVMSG %s :"%s" not found'%(chan,' '.join(line[5:])))
				todolock.release()
		elif line[3]==':snh-bot:' and line[4]=='todo-del':
			if len(line)<6:
				irc.send('PRIVMSG %s :Usage: snh-bot: todo-del TODO'%chan)
			else:
				todolock.acquire()
				t=filter((lambda x:x[0][1]==' '.join(line[5:])),zip(todo,range(len(todo))))
				if len(t)>0:
					for i,j in t:
						del todo[j]
				else:
					irc.send('PRIVMSG %s :"%s" not found'%(chan,' '.join(line[5:])))
				todolock.release()
		elif line[3]==':snh-bot:' and line[4]=='times-list':
			timeslock.acquire()
			t=map((lambda ((sh,sm),(eh,em)): '%i:%i-%i:%i'%(sh,sm,eh,em)), worktimes)
			timeslock.release()
			irc.send('PRIVMSG %s :%s'%(chan,'; '.join(t)))
		elif line[3]==':snh-bot:' and line[4]=='times-add':
			if len(line)<7:
				irc.send('PRIVMSG %s :Usage: snh-bot: times-add START END'%chan)
			else:
				run=True
				try:
					sh,sm=map(int, line[5].split(':'))
					eh,em=map(int, line[6].split(':'))
				except ValueError:
					irc.send('PRIVMSG %s :START and END must be in "hh:mm" format'%chan)
					run=False
				if run:
					timeslock.acquire()
					worktimes.append(((sh,sm),(eh,em)))
					timeslock.release()
		elif line[3]==':snh-bot:' and line[4]=='times-del':
			if len(line)<7:
				irc.send('PRIVMSG %s :Usage: snh-bot: times-del START END'%chan)
			else:
				run=True
				try:
					sh,sm=map(int, line[5].split(':'))
					eh,em=map(int, line[6].split(':'))
				except ValueError:
					irc.send('PRIVMSG %s :START and END must be in "hh:mm" format'%chan)
					run=False
				if run:
					timeslock.acquire()
					if ((sh,sm),(eh,em)) in worktimes:
						del worktimes[worktimes.index(((sh,sm),(eh,em)))]
					else:
						irc.send('PRIVMSG %s :%i:%i-%i:%i not found'%(((sh,sm),(eh,em)),chan))
					timeslock.release()
		elif line[3]==':snh-bot:' and line[4]=='help':
			help={'points': 'snh-bot: points    displays points',
			      'reset-points': 'snh-bot: reset-points    well duh',
			      'todo-add': 'snh-bot: todo-add PRIORITY TODO    add new task',
			      'todo-list': 'snh-bot: todo-list    list tasks, in order of priority',
			      'todo-completed': 'snh-bot: todo-completed TODO    marks task as done, gives points',
			      'todo-del': 'snh-bot: todo-del TODO    removes task',
			      'times-add': 'snh-bot: times-add START END    add new timerange to worktimes',
			      'times-list': 'snh-bot: times-list    list worktimes, in storage order',
			      'times-del': 'snh-bot: times-del START END    removes timerange from worktimes'}
			irc.send('PRIVMSG %s :%s'%(chan,' '.join([i for i in help])))
		
		elif nick in watchnicks and isworktime():
			activitylock.acquire()
			activity.append(time.time())
			activitylock.release()

def execcmd(s):
	if s[0]=='/q':
		quitflaglock.acquire()
		quitflag[0]=True
		quitflaglock.release()
