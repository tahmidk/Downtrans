// Replaces placeholders with actual words
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
function _replace_placeholders(){
  // Need a small delay to let translation load
  setTimeout(replace_placeholders, 2000);
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

// Listen for mutations to the html class name, which indicates if page is translated or not
const observer = new MutationObserver(function(mutationsList){
  mutationsList.forEach(mutation => {
    if (mutation.attributeName === 'class') {
      if (!mutation.oldValue){
        scroll_to_bottom();
      }
    }
  })
});
observer.observe(document.getElementsByTagName('html')[0], { attributes: true, attributeOldValue: true });

// Toggle function for 
$(document).ready(function(){
  $('ul').click(function(){
    $('ul').toggleClass('active')
    $('section').toggleClass('dark')
    $('.word').toggleClass('dark')
    $('.fade_div').toggleClass('dark')
    $('.ui_div_bottom').toggleClass('dark')
  })
})
$(window).scroll(function() {
  if($(window).scrollTop() + $(window).height() > $(document).height() - 100) {
    var incomplete_flag = document.getElementsByClassName("incomplete");
    if(incomplete_flag.length > 0){
      // Perform substitutions after reaching the bottom
      _replace_placeholders();
      scroll_to_top();
      // Mark page with "complete" flag
      incomplete_flag[0].className = "complete";
    }
  }
});