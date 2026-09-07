(() => {
  const source = document.currentScript.dataset.outcomeState;
  const templateUrl = "assets/teams-slack-outcome-template.html";

  fetch(templateUrl, { cache: "no-store" })
    .then((response) => {
      if (!response.ok) throw new Error(`Template request failed: ${response.status}`);
      return response.text();
    })
    .then((html) => {
          const page = html
            .replace(
              /<body data-outcome-state="epic-1">[\s\S]*?<header class="io-toolbar">/,
              `<body data-outcome-state="${source}">
  <div id="channel-app" hidden></div>
  <main class="cs-container cs-page io-page">
    <div class="io-mock-label" role="note">
      <strong data-ko="예상 상태 Mock" data-en="Expected state mock">예상 상태 Mock</strong>
      <span data-ko="미출시 기능의 합성 데모입니다. 버튼은 백엔드 작업을 실행하지 않습니다." data-en="Synthetic demonstration of unshipped functionality. Controls do not invoke a backend.">미출시 기능의 합성 데모입니다. 버튼은 백엔드 작업을 실행하지 않습니다.</span>
    </div>

    <header class="io-toolbar">`
            )
            ;
      document.open();
      document.write(page);
      document.close();
    })
    .catch(() => {
      document.body.innerHTML = '<main><p role="alert">Unable to load the expected-state mock.</p></main>';
    });
})();
