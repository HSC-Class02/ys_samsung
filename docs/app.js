fetch("data/metrics.json").then(function(r){return r.json();}).then(function(d){
  document.getElementById("status").textContent=d.latest_annual?"Latest period: "+d.latest_annual.period:"구조화 재무데이터가 없습니다.";
}).catch(function(e){document.getElementById("status").textContent="데이터 로드 실패: "+e.message;});
