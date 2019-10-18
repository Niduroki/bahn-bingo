$(function(){
    $("div.bingo-square").bind("taphold", tapholdHandler);

    function tapholdHandler(event){
        if (event.target.classList.contains("checked")) {
            // UNDO
            var undo_url = event.target.dataset.undoUrl;
            $.ajax({
                success: function(data){
                        if (confirm("Dieses Feld rückgängig machen?")) {
                            $(event.target).removeClass("checked");
                        }
                },
                type: "POST",
                url: undo_url,
            });
        } else {
            // SUBMIT
            var submit_url = event.target.dataset.submitUrl;
            $.ajax({
                success: function(data){
                    if (data.data === "success") {
                        $(event.target).addClass("checked");
                    } else if (data.data === "finished") {
                        $(event.target).addClass("checked");
                        alert("Was für ein D-Bakel. Punktestand: " + data.score);
                        document.cookie = "";
                        window.location = "/";
                    }
                },
                type: "POST",
                url: submit_url,
            });
        }
    }
});