const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const code = fs.readFileSync('knowte/web/app.js', 'utf8');
const select = () => ({value:'', options:[], replaceChildren(...items) {this.options=items;}, appendChild(item) {this.options.push(item);}});
const subscription = select();
const context = {document:{querySelector:()=>subscription}, Option:function(text,value){this.text=text; this.value=value;},
 aiModelProfiles:[{id:'m', name:'Model', capabilities:['chat']}], aiRoleAssignments:{intelligent_search:'m', subscription_verify:'m'},
 searchAIReview:false, searchMode:'keyword', setSearchMode() {},
};
for (const key of ['searchModelSelect','sourceDiscoveryModelSelect','evidenceModelSelect','claimsModelSelect','claimAuditModelSelect','wikiModelSelect','articleModelSelect']) context[key]=select();
vm.createContext(context);
vm.runInContext(code.slice(code.indexOf('const renderActionModelSelectors ='),code.indexOf('const renderAIProfiles ='))+'this.render=renderActionModelSelectors;',context);
context.render(true);
assert.equal(context.searchModelSelect.options[0].text,'No model');
assert.equal(subscription.options[0].text,'No model');
context.searchModelSelect.value=''; subscription.value='';
context.render();
assert.equal(context.searchModelSelect.value,'');
assert.equal(subscription.value,'');
assert.equal(context.searchAIReview,false);
context.searchModelSelect.value='m'; context.render();
assert.equal(context.searchAIReview,true);
const html=fs.readFileSync('knowte/web/index.html','utf8');
assert.ok(!html.includes('id="search-ai-review"'));
assert.ok(!html.includes('id="subscription-verify"'));
console.log('PASS No model disables verification and survives model-selector refresh');
