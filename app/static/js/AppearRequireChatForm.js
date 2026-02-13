const uploadButton = document.getElementsByName('file_load')[0];

const jsonDiffTag = document.getElementById('json-diff');
const divDetails = jsonDiffTag.getElementsByTagName('details');
console.log(divDetails);
const selectFrom = document.getElementsByClassName('select-attendance')[0];

// if (divDetails[0].children.length === 0) {
//     console.log(`${divDetails[0].children.length}`);
//     selectFrom.style.display = 'none';
// }
jsonDiffTag.addEventListener('reloaded', (event) => {
    console.log(`${JSON.stringify(divDetails)}`);
    //     if (divDetails == undefined) {
    //         selectFrom.style.display = 'none';
    //     }
});
