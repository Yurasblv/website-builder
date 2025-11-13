from enum import StrEnum


class MouseEvent(StrEnum):
    MOVE = "move"
    CLICK = "click"
    SCROLL = "scroll"


class SeleniumScript(StrEnum):
    ADD_CURSOR = """
        var style = document.createElement('style');
        style.innerHTML = '* { cursor: none; } ' +
            '.custom-cursor { position: absolute; width: 15px; height: 15px; background: red; ' +
            'border-radius: 50%; pointer-events: none; z-index: 9999; }';
        document.head.appendChild(style);
        var cursor = document.createElement('div');
        cursor.classList.add('custom-cursor');
        document.body.appendChild(cursor);
        document.addEventListener('mousemove', function(e) {
            cursor.style.left = e.pageX + 'px';
            cursor.style.top = e.pageY + 'px';
        });
        document.addEventListener('click', function() {
            cursor.style.width = '30px';
            cursor.style.height = '30px';
            setTimeout(function() {
                cursor.style.width = '15px';
                cursor.style.height = '15px';
            }, 100);
        });
    """

    ADD_ANCHOR = """
    var anchor = document.createElement('div');
    anchor.id = 'selenium-anchor';
    anchor.style.position = 'absolute';
    anchor.style.top = '0';
    anchor.style.left = '0';
    document.body.appendChild(anchor);
    """

    REMOVE_ANCHOR = """
    var anchor = document.getElementById('selenium-anchor');
    anchor.remove();
    """

    GET_SCROLL_CORDS = """return [window.scrollX, window.scrollY];"""
