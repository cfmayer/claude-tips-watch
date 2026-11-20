(function(){
  var $=function(id){return document.getElementById(id)};
  var q=$('q'),au=$('author'),ed=$('edition'),sc=$('subcat'),ty=$('type'),status=$('status'),none=$('none');
  var chips=[].slice.call(document.querySelectorAll('.chip'));
  var cards=[].slice.call(document.querySelectorAll('#browse .card'));
  var subs=[].slice.call(document.querySelectorAll('#browse section.subcat'));
  var topics=[].slice.call(document.querySelectorAll('#browse section.topic'));
  var total=document.querySelectorAll('#browse .card:not(.mirror) .t').length;
  var active=null;
  function params(){var p=new URLSearchParams(location.search);
    if(p.get('q'))q.value=p.get('q');if(p.get('author'))au.value=p.get('author');if(p.get('topic'))active=p.get('topic');
    if(p.get('edition'))ed.value=p.get('edition');if(p.get('subcat'))sc.value=p.get('subcat');if(p.get('type'))ty.value=p.get('type');}
  function sync(){var p=new URLSearchParams();if(q.value)p.set('q',q.value);if(au.value)p.set('author',au.value);if(active)p.set('topic',active);
    if(ed.value)p.set('edition',ed.value);if(sc.value)p.set('subcat',sc.value);if(ty.value)p.set('type',ty.value);
    var s=p.toString();history.replaceState(null,'',s?'?'+s+location.hash:location.pathname+location.hash);}
  function run(){
    var terms=q.value.toLowerCase().trim().split(/\s+/).filter(Boolean),a=au.value,e=ed.value,s=sc.value,y=ty.value;
    chips.forEach(function(c){c.setAttribute('aria-pressed',c.dataset.topic===active?'true':'false')});
    var any=terms.length||a||active||e||s||y,shown=0,srcShown=0,visibleSrc={};
    function pass(el,head){
      if(a&&el.dataset.author!==a)return false;
      if(active&&el.dataset.topic!==active)return false;
      if(s&&el.dataset.subcat!==s)return false;
      if(e&&el.dataset.edition!==e)return false;
      var txt=(el.dataset.search||'')+' '+head;
      return terms.every(function(t){return txt.indexOf(t)>=0});
    }
    var placed=!!(active||s); // topic/subcategory filter: show each source where its matching tips are filed (mirrors), not only at home
    cards.forEach(function(c){
      var mirror=c.classList.contains('mirror');
      if(y&&c.dataset.type!==y||(mirror&&!placed)){c.hidden=true;return}
      if(placed&&(active&&c.dataset.topic!==active||s&&c.dataset.subcat!==s)){c.hidden=true;return}
      var head=c.dataset.head,ts=[].slice.call(c.querySelectorAll('.t')),n=0;
      if(!ts.length){var ok=pass(c,c.dataset.head);c.hidden=!ok;if(ok)srcShown++;return}
      ts.forEach(function(t){var ok=pass(t,head)&&(!placed||t.dataset.subcat===c.dataset.subcat);t.hidden=!ok;if(ok){n++;if(!mirror)visibleSrc[c.id+'|'+t.dataset.subcat]=1}});
      shown+=n;c.hidden=n===0;if(n)srcShown++;
    });
    subs.forEach(function(x){
      [].slice.call(x.querySelectorAll('.seealso li')).forEach(function(li){li.hidden=placed||!visibleSrc[li.dataset.src+'|'+li.dataset.subcat]});
      var sa=x.querySelector('.seealso');if(sa)sa.hidden=!sa.querySelector('li:not([hidden])');
      x.hidden=!x.querySelector('.card:not([hidden]),.seealso li:not([hidden])');
    });
    topics.forEach(function(t){t.hidden=!t.querySelector('section.subcat:not([hidden])')});
    none.hidden=!any||shown>0||!!document.querySelector('#browse .card:not([hidden])');
    status.textContent=any?(shown+' of '+total+' tips match, from '+srcShown+' source'+(srcShown===1?'':'s')):'';
    sync();
  }
  chips.forEach(function(c){c.addEventListener('click',function(){active=active===c.dataset.topic?null:c.dataset.topic;run()})});
  q.addEventListener('input',run);[au,ed,sc,ty].forEach(function(x){x.addEventListener('change',run)});
  var only=$('only-latest');if(only)only.addEventListener('click',function(){ed.value=ed.value===only.dataset.edition?'':only.dataset.edition;run();only.textContent=ed.value?'Show all editions':'Show only this edition';$('topics').scrollIntoView()});
  $('clear').addEventListener('click',function(){q.value='';au.value='';ed.value='';sc.value='';ty.value='';active=null;run()});
  document.addEventListener('keydown',function(ev){if(ev.key==='/'&&document.activeElement!==q&&!/^(INPUT|SELECT|TEXTAREA)$/.test(document.activeElement.tagName)){ev.preventDefault();q.focus()}if(ev.key==='Escape'&&document.activeElement===q){q.value='';run()}});
  params();run();
})();
