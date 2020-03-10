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
    $('.content_raw').toggleClass('dark')
    $('.scroll_bar').toggleClass('dark')
    $('.scroll_notch').toggleClass('dark')
  })

  // Credit to Codegrid for scroll indicator script: https://www.youtube.com/channel/UC7pVho4O31FyfQsZdXWejEw
  $(window).scroll(function() {
    var winTop = $(window).scrollTop();
    var docHeight = $(document).height();
    var winHeight = $(window).height();

    var percent_scrolled = (winTop / (docHeight - winHeight))*100;
    $('.scroll_bar').css('height', percent_scrolled + '%');
    document.querySelector('.scroll_notch').innerText = Math.round(percent_scrolled) + '%';
  });
})

function bind_all_lines()
{
  var content_lines = document.getElementsByClassName('content_line');
  for(let l of content_lines){
    // First line doesn't need the following binding
    if(l.id == 'l1'){
      continue;
    }

    var line = document.getElementById(l.id)
    $(line).on('DOMSubtreeModified', line, function() {
      // Basically, when Google Trans starts translating line(n) (aka. this line) this 
      // func will replace the placeholders in line(n-1)
      var prev_line_num = this.id.substring(1) - 1;
      var line_n = document.querySelector('.content_line#l'+prev_line_num);

      if(prev_line_num == 47){
        console.log("A");
      }

      // No more need to listen to changes in line(n-1). This function will handle all
      // necessary postprocessing in one go
      $(line_n).unbind();

      var placeholders = line_n.getElementsByClassName('placeholder')
      // Replace each placeholder on this line
      for(let elem of placeholders){
        if( elem.innerHTML.toLowerCase().includes("placeholder") ){
          var word = document.getElementById('w' + elem.id).innerHTML;
          var pattern = new RegExp("(?:the\\s|a\\s)?placeholder", 'gi');

          // Pay attention to which mode it is
          if(document.querySelector("section").classList.contains('dark'))
            var replacement = "<span class=\'word dark\'>" + word + "</span>"
          else
            var replacement = "<span class=\'word\'>" + word + "</span>"

          elem.innerHTML = elem.innerHTML.replace(pattern, replacement);
        }
      }

      // At this point, translation and substitution for this line is complete. Do
      // some post processing (like remove unnecessary articles) to increase readability
      var siblingPlaceholders = 
        document.querySelectorAll('.content_line#l'+prev_line_num+' font .placeholder');
      for(let placeholder_elem of siblingPlaceholders)
      {
        var preceding_elem = placeholder_elem.previousSibling;
        if(preceding_elem != null)
        {
          var remove_articles = new RegExp("(the|a)(\\s*)$", 'gi');
          preceding_elem.innerText = preceding_elem.innerText.replace(remove_articles, "$2");
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
