// Sidebar mobile toggle
document.addEventListener('DOMContentLoaded', function () {
  var toggle = document.getElementById('mobileToggle');
  var sidebar = document.getElementById('sidebar');
  var overlay = document.getElementById('sidebarOverlay');

  function closeSidebar() {
    sidebar && sidebar.classList.remove('open');
    overlay && overlay.classList.remove('open');
  }

  if (toggle && sidebar && overlay) {
    toggle.addEventListener('click', function () {
      sidebar.classList.toggle('open');
      overlay.classList.toggle('open');
    });
    overlay.addEventListener('click', closeSidebar);
  }

  // Generic dropdown handling (notification bell, user menu)
  var triggers = document.querySelectorAll('[data-dropdown-trigger]');
  triggers.forEach(function (trigger) {
    var menuId = trigger.getAttribute('data-dropdown-trigger');
    var menu = document.getElementById(menuId);
    if (!menu) return;

    trigger.addEventListener('click', function (e) {
      e.stopPropagation();
      var isOpen = menu.classList.contains('open');
      document.querySelectorAll('.dropdown-menu.open').forEach(function (m) {
        m.classList.remove('open');
      });
      if (!isOpen) menu.classList.add('open');
    });
  });

  document.addEventListener('click', function () {
    document.querySelectorAll('.dropdown-menu.open').forEach(function (m) {
      m.classList.remove('open');
    });
  });

  // Auto-dismiss alerts
  document.querySelectorAll('.alert-close').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var alertEl = btn.closest('.alert');
      if (alertEl) alertEl.remove();
    });
  });

  // Confirm dialogs for destructive actions (delete buttons that open a modal-less confirm)
  document.querySelectorAll('[data-confirm]').forEach(function (el) {
    el.addEventListener('submit', function (e) {
      var msg = el.getAttribute('data-confirm');
      if (!window.confirm(msg)) {
        e.preventDefault();
      }
    });
  });
});
