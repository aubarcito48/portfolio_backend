import json,re,subprocess,sys
from pathlib import Path
from urllib.request import Request,urlopen,build_opener,HTTPRedirectHandler
from urllib.error import HTTPError
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parent.parent
BASE='https://portfolio-backend-6ecn.onrender.com'
FRONT='https://portfolio-nahuel48.vercel.app'
class NoRedirect(HTTPRedirectHandler):
 def redirect_request(self,*args): return None

def fetch(url,method='GET',origin=None,redirect=True):
 headers={'Accept':'application/json' if '/api/' in url else '*/*'}
 if origin:headers['Origin']=origin
 req=Request(url,method=method,headers=headers)
 try:r=(urlopen(req,timeout=90) if redirect else build_opener(NoRedirect).open(req,timeout=90))
 except HTTPError as error:r=error
 with r:return r.status,r.headers,r.read().decode('utf-8',errors='replace'),r.geturl()

def main():
 report={'case':'BE-CP25','checkedAtUtc':datetime.now(timezone.utc).isoformat(),'backend':BASE,'frontend':FRONT,'localRepositoryCommit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'deployedCommit':None,'checks':{},'pending':['Runtime database identity, settings and check --deploy inside Render','Successful administrative login with authorized user','Restart Render and compare data before/after','Record actual deployed commit from Render']}
 checks=report['checks'];baseline=json.loads((ROOT/'reports/supabase-transfer-execution.json').read_text())['summary']['counts']
 status,h,b,url=fetch(BASE+'/health/');checks['readiness']={'status':status,'genericJson':json.loads(b)=={'status':'ok'},'https':url.startswith('https://')}
 status,h,b,url=fetch('http://portfolio-backend-6ecn.onrender.com/health/',redirect=False);checks['httpRedirect']={'status':status,'toHttps':h.get('Location','').startswith(BASE)}
 for resource,model in [('perfil','perfil'),('tecnologias','tecnologia'),('experiencias','experiencia'),('formacion','formacion'),('proyectos','proyecto'),('enlaces','enlace')]:
  status,h,b,url=fetch(BASE+'/api/v1/'+resource+'/?page_size=100',origin=FRONT)
  data=json.loads(b);count=1 if resource=='perfil' and status==200 else data.get('count')
  checks[resource]={'status':status,'count':count,'matchesTransferCount':count==baseline['portfolio.'+model],'corsAllowed':h.get('Access-Control-Allow-Origin')==FRONT}
 status,h,b,url=fetch(BASE+'/api/v1/proyectos/',method='OPTIONS',origin=FRONT)
 checks['publicMethods']={'status':status,'allow':h.get('Allow'),'excludesWriteMethods':not any(m in h.get('Allow','').split(', ') for m in ('POST','PUT','PATCH','DELETE'))}
 status,h,b,url=fetch(BASE+'/api/v1/proyectos/',method='POST',origin=FRONT)
 checks['emptyPostRejected']={'status':status,'passed':status in (403,405),'note':'Empty POST to collection only; no record identifiers or data submitted.'}
 status,h,b,url=fetch(BASE+'/admin/login/')
 css=re.findall(r'href="([^"]+\.css[^"]*)"',b)
 cookies=h.get_all('Set-Cookie') or []
 checks['adminLogin']={'status':status,'loginFormPresent':'name="username"' in b and 'name="password"' in b,'csrfCookieSecure':any(x.startswith('csrftoken=') and re.search(r';\s*Secure(?:;|$)',x,re.I) is not None for x in cookies),'styles':{}}
 for item in css:
  if item.startswith('/static/'):
   code,ch,content,_=fetch(BASE+item)
   checks['adminLogin']['styles'][item]={'status':code,'cssContentType':'text/css' in ch.get('Content-Type','')}
 status,h,b,url=fetch(BASE+'/admin/portfolio/proyecto/',redirect=False)
 checks['anonymousAdminRestricted']={'status':status,'redirectToLogin':h.get('Location','').startswith('/admin/login/')}
 status,h,b,url=fetch(BASE+'/tk18-path-that-does-not-exist/')
 checks['generic404']={'status':status,'noDebugTrace':all(x not in b for x in ('Django tried these URL patterns','Using the URLconf defined','Traceback (most recent call last)'))}
 status,h,b,url=fetch(BASE+'/health/',origin='https://untrusted.invalid')
 checks['untrustedCorsDenied']={'status':status,'noAllowOrigin':not h.get('Access-Control-Allow-Origin')}
 report['result']='partial_pending_private_runtime_evidence'
 (ROOT/'reports/TK18-production-verification.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
 print(json.dumps(report,indent=2))
if __name__=='__main__':main()
