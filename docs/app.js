fetch("data/metrics.json").then(function(r){return r.json();}).then(function(d){
  var l=d.latest_annual;
  document.getElementById("status").textContent=l?"Latest structured annual period: "+l.period+" · Generated "+new Date(d.generated_at).toLocaleString("ko-KR"):"구조화 재무데이터가 없습니다.";
  renderKpis(l);
  renderTable(document.getElementById("annualTable"),d.annual||[]);
  renderTable(document.getElementById("halfTable"),d.half||[]);
  renderTable(document.getElementById("quarterTable"),d.quarterly||[]);
  charts(d.annual||[]);
}).catch(function(e){document.getElementById("status").textContent="데이터 로드 실패: "+e.message;});
