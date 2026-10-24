// Static-source browser acceptance. No CKB server is started and no live API is contacted.
const fs=require('fs'),path=require('path');
(async()=>{
 const cfg=JSON.parse(fs.readFileSync(0,'utf8'));
 const {chromium}=require(require.resolve('playwright',{paths:[cfg.moduleRoot]}));
 const candidateRoot=path.resolve(cfg.root),baselineRoot=cfg.baselineRoot?path.resolve(cfg.baselineRoot):null,result={pass:true,checks:[],screenshots:{}};
 const check=(name,pass,detail)=>{result.checks.push({name,pass,detail});if(!pass)result.pass=false;};
 const browser=await chromium.launch({headless:true,chromiumSandbox:true});
 const state=async(page,id,width,chart)=>{
  const el=page.locator('[id="'+id+'"]');
  let ok=await el.count()===1&&await el.isVisible();
  const box=ok?await el.boundingBox():null;
  if(chart) ok=!!box&&box.width>0&&box.height>0&&box.x<width&&box.x+box.width>0&&box.y<900&&box.y+box.height>0;
  else ok=!!box&&box.width>0&&box.height>0&&box.x>=0&&box.y>=0&&box.x+box.width<=width&&box.y+box.height<=900;
  return {ok,box};
 };
 const open=async(root,spec,width)=>{
  const ctx=await browser.newContext({viewport:{width,height:900},serviceWorkers:'block'});
  await ctx.route('**/*',async route=>{
   const u=new URL(route.request().url());
   if(u.hostname!=='ckb-plane.test'||!['http:','https:'].includes(u.protocol)){await route.abort();return;}
   const requestPath=decodeURIComponent(u.pathname).replace(/^\/+/,''),rel=requestPath.startsWith('assets/')?requestPath.slice('assets/'.length):requestPath;
   const file=path.resolve(root,rel);
   if(!file.startsWith(root+path.sep)){await route.abort();return;}
   try{const st=fs.lstatSync(file);if(!st.isFile()||st.isSymbolicLink()){await route.abort();return;}
    const types={'.html':'text/html','.js':'text/javascript','.css':'text/css','.png':'image/png','.svg':'image/svg+xml','.json':'application/json'};
    await route.fulfill({status:200,contentType:types[path.extname(file)]||'application/octet-stream',body:fs.readFileSync(file)});
   }catch{await route.fulfill({status:404,contentType:'text/plain',body:'Static acceptance: endpoint unavailable'});}
  });
  await ctx.routeWebSocket('**/*',ws=>ws.close());
  const page=await ctx.newPage(),jsErrors=[];
  page.on('pageerror',e=>jsErrors.push(e.message));
  await page.goto('http://ckb-plane.test/'+spec.Path,{waitUntil:'load',timeout:15000});
  await page.evaluate(()=>new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r))));
  return {ctx,page,jsErrors};
 };
 try{
  for(let i=0;i<cfg.pages.length;i++)for(const width of [1024,1440]){
   const spec=cfg.pages[i],cand=await open(candidateRoot,spec,width),base=baselineRoot?await open(baselineRoot,spec,width):null;
   for(const id of spec.CriticalIDs){
    const c=await state(cand.page,id,width,id===spec.ChartID);
    if(base){
     const b=await state(base.page,id,width,id===spec.ChartID);
     check('BROWSER_CRITICAL_CONTROL',!b.ok||c.ok,spec.Path+' @ '+width+': '+id+' baseline='+b.ok+' candidate='+c.ok);
    }else{
     check('BROWSER_CRITICAL_CONTROL',c.ok,spec.Path+' @ '+width+': '+id);
    }
   }
   if(spec.ChartID){
    const c=await state(cand.page,spec.ChartID,width,true);
    if(base){
     const b=await state(base.page,spec.ChartID,width,true);
     check('BROWSER_CHART_CANVAS',!b.ok||c.ok,spec.Path+' @ '+width+' baseline='+b.ok+' candidate='+c.ok);
    }else{
     check('BROWSER_CHART_CANVAS',c.ok,spec.Path+' @ '+width);
    }
   }
   check('BROWSER_SCRIPT_ERRORS',cand.jsErrors.length===0,spec.Path+' @ '+width+': '+cand.jsErrors.join('; '));
   check('BROWSER_HORIZONTAL_OVERFLOW',await cand.page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth),spec.Path+' @ '+width);
   result.screenshots['page-'+i+'-'+width+'.png']=(await cand.page.screenshot({fullPage:true})).toString('base64');
   if(base) await base.ctx.close();
   await cand.ctx.close();
  }
 }finally{await browser.close();}
 process.stdout.write(JSON.stringify(result));
})().catch(e=>{process.stderr.write(String(e));process.exitCode=1;});
