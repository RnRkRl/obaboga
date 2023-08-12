let extension_element = document.getElementById('gallery-extension').parentNode;

main_parent.addEventListener('click', function(e) {
    let chat_visible =  (chat_tab.offsetHeight > 0 && chat_tab.offsetWidth > 0);
    let notebook_visible =  (notebook_tab.offsetHeight > 0 && notebook_tab.offsetWidth > 0);
    let default_visible =  (default_tab.offsetHeight > 0 && default_tab.offsetWidth > 0);

    // Only show this extension in the Chat tab
    if (chat_visible) {
        extension_element.style.display = 'flex';
    } else {
        extension_element.style.display = 'none';
    }
});
