// Toggle function for night and day mode
$(document).ready(function()
{
  /* Bind all lines to listen to changes to their inner html contents
     This means they have been google translated at which point we can
     run the replace_placeholder procedure w/out confusing the 
     translation
  */
  bind_all_lines()

  // Add functionality to day/night mode button 
  $('ul').click(function(){
    $('ul').toggleClass('active')
    $('.pigpanda_png').toggleClass('dark')
    $('section').toggleClass('dark')
    $('.word').toggleClass('dark')
    $('.fade_div').toggleClass('dark')
    $('.ui_div_bottom').toggleClass('dark')
  })
})

/*
function bind_all_lines()
{
  var content_lines = document.getElementsByClassName('content_line');
  for(let l of content_lines){
    var line = document.getElementById(l.id)
    $(line).on('DOMSubtreeModified', line, function() {
      // Only run replacement algorithm if page is marked translated by 
      // Google Trans
      var html_elem = document.querySelector("html");
      if(html_elem.classList.contains("translated-ltr")){
        // Select all placeholder divs in this line specifically
        var line_n = document.querySelector('.content_line#'+line.id);
        var placeholders = line_n.getElementsByClassName('placeholder')
        // Replace each placeholder on this line
        for(let elem of placeholders){
          if( elem.innerHTML.toLowerCase().includes("placeholder") ){
            var word = document.getElementById('w' + elem.id).innerHTML;
            var pattern = new RegExp("placeholder", 'gi');
            var replacement = "<span class=\'word\'>" + word + "</span>"

            elem.innerHTML = elem.innerHTML.replace(pattern, replacement);
          }
        }
      }
    });
  }
}
*/

function bind_all_lines()
{
  var content_lines = document.getElementsByClassName('content_line');
  for(let l of content_lines){
    // Skip first line
    if(l.id == 'l1'){
      continue;
    }

    var line = document.getElementById(l.id)
    $(line).on('DOMSubtreeModified', line, function() {
      // Basically, when Google Trans starts translating line(n+1) will replace the 
      // placeholders in line 
      var prev_line_num = this.id.substring(1) - 1;
      var line_n = document.querySelector('.content_line#l'+prev_line_num);
      var placeholders = line_n.getElementsByClassName('placeholder')
      // Replace each placeholder on this line
      for(let elem of placeholders){
        if( elem.innerHTML.toLowerCase().includes("placeholder") ){
          var word = document.getElementById('w' + elem.id).innerHTML;
          var pattern = new RegExp("(?:the\s)?placeholder(?:s)?", 'gi');

          // Pay attention to which mode it is
          if(document.querySelector("section").classList.contains('dark'))
            var replacement = "<span class=\'word dark\'>" + word + "</span>"
          else
            var replacement = "<span class=\'word\'>" + word + "</span>"

          elem.innerHTML = elem.innerHTML.replace(pattern, replacement);
        }
      }
    });
  }
}

// Replaces ALL placeholders with their respective words (not one by one)
function replace_placeholders()
{
  var placeholders = document.getElementsByClassName('placeholder');
  for(let elem of placeholders){
    if( elem.innerHTML.toLowerCase().includes("placeholder") ){
      var word = document.getElementById('w' + elem.id).innerHTML;
      var pattern = new RegExp("placeholder", 'gi');
      var replacement = "<span class=\'word\'>" + word + "</span>"

      elem.innerHTML = elem.innerHTML.replace(pattern, replacement);
    }
  }
}

// Scroll to the very bottom of the page
function scroll_to_bottom(){
  var elmnt = document.getElementById("bottom_marker");
  elmnt.scrollIntoView({behavior: "smooth"}); 
}

// Scroll to the very top of the page
function scroll_to_top(){
  window.scrollTo({
    top: 0,
    behavior: 'smooth'
  });
}
