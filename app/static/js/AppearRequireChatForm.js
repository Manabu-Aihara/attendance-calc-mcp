const jsonDiffTag = document.getElementById('json-diff');
const selectFrom = document.getElementsByClassName('select-attendance')[0];

selectFrom.style.display = 'none';
const observer = new MutationObserver(function () {
    // 変化が発生したときの処理を記述
    console.log('divの中身が変更されたよ');
    selectFrom.style.display = 'flex';
});
const config = {
    childList: true
};
// 監視の開始
observer.observe(jsonDiffTag, config);

