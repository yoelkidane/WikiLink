let clickCounter = 0;
let startTime = Date.now();
let endPage = null;

// Function to show the navbar
function showNavbar() {
    document.getElementById("navbar").style.display = "block";
}

// Start game event
document.getElementById("start-game").addEventListener("click", function () {
    fetch('/api/challenge')
        .then(response => response.json())
        .then(data => {
            clickCounter = 0;
            startTime = Date.now();
            endPage = `/wiki/${encodeURIComponent(data.end)}`;
            window.location.href = `/wiki/${encodeURIComponent(data.start)}`;
            document.getElementById("click-counter").innerText = `Clicks: ${clickCounter}`;
            const summaryDiv = document.getElementById("article-summary");
            summaryDiv.innerHTML = `<strong>Starting Article Summary:</strong> ${data.summary_start} <br><br> 
                                    <strong>Target Article Summary:</strong> ${data.summary_end}`;
            summaryDiv.style.display = 'none';
            showNavbar();
        })
        .catch(error => {
            console.error("Failed to fetch the game challenge:", error);
        });
});

// Close the modal
document.getElementById('closeModal').addEventListener('click', function () {
    const modal = document.getElementById('winModal');
    const overlay = document.getElementById('overlay');
    modal.style.display = 'none';
    overlay.style.display = 'none';
    location.reload();
});

// Increment click counter on link clicks
document.addEventListener('click', function (e) {
    if (e.target.tagName === 'A') {
        clickCounter++;
        document.getElementById("click-counter").innerText = `Clicks: ${clickCounter}`;
        checkWinCondition(e.target.href);
    }
});

// Function to check if the clicked page is the destination
function checkWinCondition(clickedPage) {
    const clickedPathname = new URL(clickedPage, window.location.origin).pathname;
    const endPathname = new URL(endPage, window.location.origin).pathname;

    if (clickedPathname === endPathname) {
        const timeTaken = Math.round((Date.now() - startTime) / 1000);
        showWinPopup(timeTaken, clickCounter);
    }
}

// Function to show the win message in the modal
function showWinPopup(timeTaken, clickCounter) {
    const modal = document.getElementById('winModal');
    const overlay = document.getElementById('overlay');
    modal.style.display = 'block';
    overlay.style.display = 'block';
    document.getElementById('winMessage').innerText = `Congrats, you won! Your time was ${timeTaken} seconds and you visited ${clickCounter} articles.`;

    document.getElementById('tryAgainButton').onclick = function () {
        resetGame();
    };
}

// Reset the game (timer, click counter, etc.)
function resetGame() {
    clickCounter = 0;
    startTime = Date.now();
    endPage = null;
    const modal = document.getElementById('winModal');
    const overlay = document.getElementById('overlay');
    modal.style.display = 'none';
    overlay.style.display = 'none';
    window.location.href = '/';
}
