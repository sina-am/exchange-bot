async function login_user(evt) {
    const username = document.getElementById("username-input").value;
    const password = document.getElementById("password-input").value;
    const brokerName = document.getElementById("broker-name").value;

    const response = await fetch("/api/login", {
        method: 'POST',
        headers: {
            'Content-Type': "application/json"
        },
        body: JSON.stringify({
            "username": username,
            "password": password,
            "broker": brokerName,
        })
    })
    if (response.status === 200) {
        const resBody = await response.json()
        document.getElementById('message').innerHTML = resBody["message"];
    }
    else if (response.status === 422) {
        const resBody = await response.json()
        document.getElementById('message').innerHTML = resBody[0]["msg"];
    }
    else if (response.status === 400) {
        const resBody = await response.json()
        document.getElementById('message').innerHTML = resBody["message"];
    } else {
        document.getElementById('message').innerHTML = "something went wrong";
    }
}