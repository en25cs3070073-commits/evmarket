(function () {
  var frame = document.getElementById("viz-iframe");
  var loading = document.getElementById("viz-loading");
  var failed = document.getElementById("viz-failed");
  if (!frame) return;

  var settled = false;
  var timer = setTimeout(function () {
    if (settled) return;
    loading.hidden = true;
    failed.hidden = false;
  }, 20000);

  frame.addEventListener("load", function () {
    settled = true;
    clearTimeout(timer);
    frame.classList.add("is-loaded");
    loading.hidden = true;
  });

  frame.addEventListener("error", function () {
    clearTimeout(timer);
    loading.hidden = true;
    failed.hidden = false;
  });
})();
