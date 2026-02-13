window.addEventListener('DOMContentLoaded', (event) => {

    // File APIが利用できるか確認
    if (window.File && window.FileReader) {
        const elemFileLoad = document.getElementById("file_load");

        elemFileLoad.addEventListener("change", (event) => {
            const inputFile = event.target.files[0];
            // オブジェクト。ユーザーが指定したファイルを非同期で読み取る。
            const fReader = new FileReader();

            // ファイル内容の読み込み(fReader.readAsText)が正常に完了した際、コールされる
            fReader.onload = (event) => {
                const elemDisplayData = document.getElementById("json-diff");
                // file内容を取得
                // console.log(event.target.result)
                // elemDisplayData.innerHTML += event.target.result;
                const parseData = JSON.parse(event.target.result);
                const parser = new DOMParser();

                // キーと値を取得
                Object.entries(parseData).forEach(([key, value]) => {
                    let details = '<details open><summary>' + key + '</summary>';
                    // const result = value.map(item = JSON.stringify(item)).join('\n');
                    // details += '<pre><code>' + result + '</code></pre>';
                    // 「インデックス（添字）」と「その要素」のペアが返される。
                    // const arrayValue = Object.entries(value);
                    // console.log(arrayValue);
                    // 2. 各要素をJSON文字列に戻して、改行で結合
                    const result = value.map((v, k) => {
                        const diffData = '<pre><code>' + JSON.stringify(v) + '</code></pre>';
                        // const diffData = JSON.stringify(v);
                        return diffData;
                    }).join('\n');
                    // console.log(result);
                    details += result + '</details>';
                    const doc = parser.parseFromString(details, "text/html");
                    elemDisplayData.innerHTML += doc.body.innerHTML;
                }); // Object.entriesの終了
            } // fReader.onloadの終了
            // ファイル内容読み込み実施
            fReader.readAsText(inputFile);
        }); // elemFileLoadの終了
    } else {
        alert("File API is not available");
        return false;
    } // File API
}); // DOMContentLoadedの終了
