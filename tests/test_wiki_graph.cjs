const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const app = fs.readFileSync('knowte/web/app.js', 'utf8');
const context = {};
vm.runInNewContext(app.slice(app.indexOf('const wikiGraphLayout ='), app.indexOf('const wikiGraphOptions =')) + '\nthis.layout = wikiGraphLayout;', context);
const claims = Array.from({length:30}, (_,i)=>({id:String(i),statement:'Claim '+i}));
const edge = (a,b,type='supports')=>({subject_claim_id:String(a),object_claim_id:String(b),relation_type:type});
const edges = [...Array.from({length:16},(_,i)=>edge(0,i+1)),edge(17,18,'contradicts'),edge(18,19,'related')];
const wiki = {pages:[{id:'page',claim_ids:claims.map(c=>c.id)}],graph:{nodes:claims,edges}};
const check = data => {
  const result = context.layout(data);
  for (const a of result.nodes) {
    assert(Number.isFinite(a.x) && Number.isFinite(a.y));
    assert(a.x >= 0 && a.y >= 0 && a.x + 176 <= result.width && a.y + 36 <= result.height);
    for (const b of result.nodes) if (a.id !== b.id) {
      assert(Math.abs(a.x-b.x) >= 176 || Math.abs(a.y-b.y) >= 36, 'node labels overlap');
    }
  }
  return result;
};
const graph = check(wiki);
assert.equal(graph.nodes.length,20);
assert.equal(graph.isolated.length,10);
assert.equal(graph.groupCount,2);
assert.equal(graph.edges.length,18);
assert.deepEqual(context.layout({...wiki,pages:[]}),graph,'Wiki pages cannot affect relation placement');
assert.deepEqual(context.layout(wiki),graph,'layout is deterministic');
assert.equal(check({graph:{nodes:claims,edges:[]}}).isolated.length,30);
assert.equal(check({graph:{nodes:[],edges:[]}}).nodes.length,0);
assert.equal(check({graph:{nodes:claims,edges:[edge(0,0),edge(0,999),edge(0,1,'contains')]}}).edges.length,0);
const denseEdges = [];
for (let i=0;i<20;i++) for (let j=i+1;j<20;j++) denseEdges.push(edge(i,j));
check({graph:{nodes:claims,edges:denseEdges}});
const many = Array.from({length:250},(_,i)=>({id:String(i),statement:'Large graph '+i}));
check({graph:{nodes:many,edges:many.slice(1).map((_,i)=>edge(i,i+1))}});
console.log('PASS page-independent deterministic components, dense/large graphs, collision bounds and unconnected Claims');

const selectCode = app.slice(app.indexOf('  const select = id =>', app.indexOf('const renderWikiGraph =')), app.indexOf('  const createNode =', app.indexOf('const renderWikiGraph =')));
let fitted = 0, updated = 0;
const selection = {options:{selected:'',focused:false}, tooltip:{hidden:false}, updateSelection:()=>updated++, fit:()=>fitted++};
vm.runInNewContext(selectCode + '\nthis.select = select;', selection);
selection.select('a'); assert.equal(selection.options.selected,'a');
selection.select('a'); assert.equal(selection.options.selected,''); assert.equal(fitted,0);
selection.select('b'); selection.options.focused = true;
selection.select('b'); assert.equal(selection.options.focused,false); assert.equal(selection.options.selected,''); assert.equal(fitted,1);
selection.select('a'); selection.options.focused = true;
selection.select('b'); assert.equal(selection.options.selected,'b'); assert.equal(selection.options.focused,true); assert.equal(fitted,2);
assert.equal(updated,6);
const wheelCode = app.slice(app.indexOf('  viewport.addEventListener("wheel"', app.indexOf('const renderWikiGraph =')), app.indexOf('  const legend =', app.indexOf('const renderWikiGraph =')));
for (const isMac of [false,true]) {
  let handler, zooms = 0, prevented = 0;
  vm.runInNewContext(wheelCode, {isMac, viewport:{addEventListener:(name, callback)=>{handler=callback;},getBoundingClientRect:()=>({left:0,top:0})}, zoom:()=>zooms++});
  const event = {deltaY:40,clientX:10,clientY:10,ctrlKey:false,metaKey:false,preventDefault:()=>prevented++};
  handler(event); assert.equal(zooms,0); assert.equal(prevented,0,'ordinary scrolling must pass through');
  handler({...event,ctrlKey:true}); assert.equal(zooms,1,'Ctrl-wheel / pinch zooms');
  handler({...event,metaKey:true}); assert.equal(zooms,isMac?2:1,'Cmd-wheel is enabled on Mac');
  assert.equal(prevented,zooms);
}
console.log('PASS node toggle, focused deselection, ordinary scroll passthrough and modifier/pinch zoom');
