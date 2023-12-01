//
// function to toggle a box between open/close
//
function toggleContent(boxId) {
    var box = document.getElementById(boxId);
    var content = box.querySelector('.folding_box_content');
    var isContentExpanded = content.classList.contains('open');
    var header = box.querySelector('.folding_box_header');

    console.log("isContentExpanded:", isContentExpanded);
    if (isContentExpanded) {
        content.classList.remove('open');
        header.classList.remove('open');
    } else {
        content.classList.add('open');
        header.classList.add('open');
    }
}