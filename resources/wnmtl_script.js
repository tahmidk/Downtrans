// Toggle function for night and day mode and bind all lines for processing
$(document).ready(function()
{
  /* Bind all lines to listen to changes to their inner html contents
     This means they have been google translated at which point we can
     run the replace_placeholder procedure w/out confusing the 
     translation
  */
  bind_all_lines();

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

function replace_placeholders_in_line(line_num)
{
  // Validity check
  if(line_num <= 0)
    return;

  var line_elem = document.querySelector('.content_line#l'+line_num);
  var placeholders = line_elem.getElementsByClassName('placeholder')
  // Replace each placeholder on this line
  for(let elem of placeholders){
    if( elem.innerHTML.toLowerCase().includes("placeholder") ){
      var word = document.getElementById('w' + elem.id).innerHTML;
      var pattern = new RegExp("(?:the\\s|a\\s)?placeholder", 'gi');

      // Pay attention to which mode it is
      if(document.querySelector("section").classList.contains('dark'))
        var replacement = "<span class=\'notranslate word dark\'>" + word + "</span>";
      else
        var replacement = "<span class=\'notranslate word\'>" + word + "</span>";

      elem.innerHTML = elem.innerHTML.replace(pattern, replacement);
    }
  }

  // At this point, translation and substitution for this line is complete. Do
  // some post processing (like remove unnecessary articles) to increase readability
  var siblingPlaceholders = 
    document.querySelectorAll('.content_line#l'+line_num+' font .placeholder');
  for(let placeholder_elem of siblingPlaceholders)
  {
    var preceding_elem = placeholder_elem.previousSibling;
    if(preceding_elem != null && !preceding_elem.classList.contains("placeholder"))
    {
      var remove_articles = new RegExp("(the|a)(\\s*)$", 'gi');
      preceding_elem.innerText = preceding_elem.innerText.replace(remove_articles, "$2");
    }
  }
}

function bind_all_lines()
{
  var dummies = document.getElementsByClassName('dummy');
  var checkpoint = new Array(dummies.length).fill(false);
  var line_processed = new Array(dummies.length - 1).fill(false);
  for(let d of dummies){
    var dummy = document.getElementById(d.id);
    $(dummy).on('DOMSubtreeModified', dummy, function() {
      $(this).unbind();
      // A dummy is "triggered" when it's touched by google translate
      var dummy_curr_id = parseInt(this.id.substring(1));
      checkpoint[dummy_curr_id] = true;

      // If D and D-1 are both triggered, then the line between them, L=D-1
      // should be completely translated and ready to postprocess
      var dummy_prev_id = dummy_curr_id - 1;
      if(dummy_prev_id > 0 && checkpoint[dummy_prev_id]){
        if(!line_processed[dummy_prev_id]){
          replace_placeholders_in_line(dummy_prev_id);
          line_processed[dummy_prev_id] = true;
        }
      }

      // If D and D+1 are both triggered, then the line between them, L=D
      // should be completely translated and ready to postprocess
      var dummy_next_id = dummy_curr_id + 1;
      if(dummy_next_id < checkpoint.length && checkpoint[dummy_next_id]){
        if(!line_processed[dummy_curr_id]){
          replace_placeholders_in_line(dummy_curr_id);
          line_processed[dummy_curr_id] = true;
        }
      }
    });
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
