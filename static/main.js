$(function(){
    $("div.bingo-square").bind("taphold", tapholdHandler);
    $("#giveup").bind("taphold", giveupHandler);

    function tapholdHandler(event){
        event.preventDefault();
        var parent = false;
        if (
            event.target.classList.contains("checked") ||
            event.target.parentNode.classList.contains("checked")
        ) {
            // UNDO
            var undo_url = event.target.dataset.undoUrl;
            if (undo_url === undefined) {
                undo_url = event.target.parentNode.dataset.undoUrl;
                parent = true;
            }
            if (confirm("Dieses Feld rückgängig machen?")) {
                $.ajax({
                    success: function(data){
                            if (parent) {
                                $(event.target.parentNode).removeClass("checked");
                            } else {
                                $(event.target).removeClass("checked");
                            }
                    },
                    type: "POST",
                    url: undo_url,
                });
            }
        } else {
            // SUBMIT
            var submit_url = event.target.dataset.submitUrl;
            if (submit_url === undefined) {
                submit_url = event.target.parentNode.dataset.submitUrl;
                parent = true;
            }
            $.ajax({
                success: function(data){
                    if (data.data === "success" || data.data === "finished") {
                        if (parent) {
                            $(event.target.parentNode).addClass("checked");
                        } else {
                            $(event.target).addClass("checked");
                        }
                    }
                    if (data.data === "finished") {
                        document.cookie = "";
                        alert("Was für ein D-Bakel. Punktestand: " + data.score);
                        window.location = "/";
                    }
                    if (data.data === "cheater") {
                        document.cookie = "";
                        alert("Cheater.");
                        window.location = "/";
                    }
                },
                type: "POST",
                url: submit_url,
            });
        }
    }

    function giveupHandler(event){
        event.preventDefault();
        if (confirm("Aufgeben, und Bingo-Feld beenden?")) {
            var quit_url = event.target.dataset.quitUrl;
            if (quit_url === undefined) {
                quit_url = event.target.parentNode.dataset.quitUrl;
            }
            $.ajax({
                success: function(data){
                    document.cookie = "";
                    window.location = "/";
                },
                type: "POST",
                url: quit_url,
            });
        }
    }
});