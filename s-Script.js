document.addEventListener('DOMContentLoaded', function () {
  // Smooth scroll for anchor links
  document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
      e.preventDefault();
      document.querySelector(this.getAttribute('href')).scrollIntoView({
        behavior: 'smooth'
      });
    });
  });

  // Animated logo: Toggle between 'J' and 'K' for the first letter
  const logoLetter = document.getElementById('logo-letter');
  let toggle = false;
  setInterval(() => {
    logoLetter.classList.add('roll-animation');
    // Change letter halfway through the roll animation (after 500ms)
    setTimeout(() => {
      logoLetter.textContent = toggle ? 'J' : 'K';
    }, 500);
    // Remove the animation class after 1 second and toggle for next round
    setTimeout(() => {
      logoLetter.classList.remove('roll-animation');
      toggle = !toggle;
    }, 1000);
  }, 5000);
});
