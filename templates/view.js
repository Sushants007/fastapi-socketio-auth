const startTime = '{{ start_time }}'
    const currentUser = '{{ current_user }}'
    const PORT = '{{ PORT }}'

        if (window.location.protocol == "https:") {
            var ws_scheme = "wss://";
        } else {
            var ws_scheme = "ws://"
        };

    const socket = io(ws_scheme + location.host, {path: '/ws/socket.io/'});

    socket.on('new user', data => {
        socket.user = data.username
        console.log({ data });
    });

    socket.on('message', text => {
        const el = document.createElement('li');
        el.innerHTML = text + socket.user;
        document.querySelector('ul').appendChild(el);
    });


    document.getElementById('sendBtn').onclick = () => {
        const text = document.getElementById('textInput').value;
        socket.emit('message', text)
    }

    const logoutBtn = document.getElementById('logoutBtn')

    socket.on('logout', userName => {
        if ( currentUser === userName) {
            socket.disconnect();
            logoutBtn.click();
        }
    });
