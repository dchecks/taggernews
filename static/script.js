function hideTooltip() {
    clearTimeout(tooltipTimeout);
    $(".tooltip").fadeOut().remove();
}

function showTooltip(elementId){
    var user = elementId.substr(7);
    console.log("Loading tooltip for " + user);
    $.getJSON("/user?id=" + user, function(data) {
        var outstr = "";
        for(key in data) {
            outstr += "<span class='tag'>" + key + "</span> " + data[key] + "<br />";
        }

        var tooltip = $("<div id='tooltip' class='tooltip'>" + outstr+ "</div>");
        tooltip.appendTo($("#" + elementId));
    })
    .fail(function(data){
        var tooltip = $("<div id='tooltip' class='tooltip'>" + data['message'] + "</div>");
        tooltip.appendTo($("#" + elementId));
    });
}

$(".hnuser").hover(function(e) {
    tooltipTimeout = setTimeout(function() { showTooltip(e.target.id) }, 1000);},
    hideTooltip);
