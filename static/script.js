function hideTooltip() {
    clearTimeout(tooltipTimeout);
    $(".tooltip").fadeOut().remove();
}

function popup(data, elementId) {
    var outstr = "";
    for(key in data) {
        outstr += "<span class='tag'>" + key + "</span> " + data[key] + "<br />";
    }

    var tooltip = $("<div id='tooltip' class='tooltip'>" + outstr+ "</div>");
    tooltip.appendTo($("#" + elementId));
}

 function fail(data, elementId){
    var tooltip = $("<div id='tooltip' class='tooltip'>" + data['message'] + "</div>");
    tooltip.appendTo($("#" + elementId));
}

function showTooltip(elementId){
    var user = elementId.substr(7);
    console.log("Loading tooltip for " + user);

    $.ajax({
      dataType: "json",
      url: "/user?id=" + user,
      statusCode:{
        200: function(data) {
            popup(data, elementId);
        },
        404: function(data) {
            fail(data, elementId);
        }
      }
    });


}

$(".hnuser").hover(function(e) {
    tooltipTimeout = setTimeout(function() { showTooltip(e.target.id) }, 1000);},
    hideTooltip);

