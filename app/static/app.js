const { createApp, ref, onMounted, watch } = Vue;

createApp({
  setup() {
    const me = ref(null);

    const loginForm = ref({ username: '', password: '' });
    const registerForm = ref({ username: '', password: '' });
    const showRegister = ref(false);

    const globalError = ref('');
    const globalMessage = ref('');
    const loading = ref(false);

    const adminDashboard = ref(null);
    const userDashboard = ref(null);

    const adminTab = ref('dashboard');

    const newLot = ref({
      name: '',
      address: '',
      pincode: '',
      price_per_hour: '',
      max_spots: ''
    });
    const editLot = ref({
      id: null,
      name: '',
      address: '',
      pincode: '',
      price_per_hour: '',
      max_spots: ''
    });

    let adminRevenueChart = null;
    let adminOccupancyChart = null;
    let adminUserStatusChart = null;
    let userLotUsageChart = null;

    const clearMessages = () => {
      globalError.value = '';
      globalMessage.value = '';
    };

    const formatDateTime = (isoString) => {
      if (!isoString) return '';
      const d = new Date(isoString);
      if (isNaN(d)) return isoString;
      return d.toLocaleString();
    };

    const fetchMe = async () => {
      try {
        const res = await fetch('/api/me');
        const data = await res.json();
        me.value = data.user;
        if (me.value) {
          if (me.value.role === 'admin') {
            await loadAdminDashboard();
          } else {
            await loadUserDashboard();
          }
        }
      } catch (e) {
        console.error(e);
      }
    };

    const apiLogin = async () => {
      clearMessages();
      loading.value = true;
      try {
        const res = await fetch('/api/login', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(loginForm.value),
        });
        const data = await res.json();
        if (!res.ok) {
          globalError.value = data.error || 'Login failed';
          return;
        }
        globalMessage.value = data.message || 'Login successful';
        me.value = data.user;
        loginForm.value.password = '';

        if (me.value.role === 'admin') {
          await loadAdminDashboard();
        } else {
          await loadUserDashboard();
        }
      } catch (e) {
        globalError.value = 'Network error';
      } finally {
        loading.value = false;
      }
    };

    const apiRegister = async () => {
      clearMessages();
      loading.value = true;
      try {
        const res = await fetch('/api/register', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(registerForm.value),
        });
        const data = await res.json();
        if (!res.ok) {
          globalError.value = data.error || 'Registration failed';
          return;
        }
        globalMessage.value = data.message || 'Registration successful. Please log in.';
        registerForm.value = { username: '', password: '' };
        showRegister.value = false;
      } catch (e) {
        globalError.value = 'Network error';
      } finally {
        loading.value = false;
      }
    };

    const apiLogout = async () => {
      clearMessages();
      loading.value = true;
      try {
        const res = await fetch('/api/logout', { method: 'POST' });
        const data = await res.json();
        if (!res.ok) {
          globalError.value = data.error || 'Logout failed';
          return;
        }
        globalMessage.value = data.message || 'Logged out';
        me.value = null;
        adminDashboard.value = null;
        userDashboard.value = null;
      } catch (e) {
        globalError.value = 'Network error';
      } finally {
        loading.value = false;
      }
    };

    const apiExportCsv = async () => {
      clearMessages();
      loading.value = true;
      try {
        const res = await fetch('/api/user/export_csv', { method: 'POST' });
        const data = await res.json();
        if (!res.ok) {
          globalError.value = data.error || 'Export failed';
          return;
        }
        globalMessage.value = data.message || 'Export started. Check your email.';
      } catch (e) {
        globalError.value = 'Network error';
      } finally {
        loading.value = false;
      }
    };

    const loadAdminDashboard = async () => {
      if (!me.value || me.value.role !== 'admin') return;
      try {
        const res = await fetch('/api/admin/dashboard');
        const data = await res.json();
        if (res.ok) {
          adminDashboard.value = data;
        }
      } catch (e) {
        console.error(e);
      }
    };

    const loadUserDashboard = async () => {
      if (!me.value || me.value.role !== 'user') return;
      try {
        const res = await fetch('/api/user/dashboard');
        const data = await res.json();
        if (res.ok) {
          userDashboard.value = data;
        }
      } catch (e) {
        console.error(e);
      }
    };

    const refreshCurrent = async () => {
      clearMessages();
      if (!me.value) return;
      if (me.value.role === 'admin') {
        await loadAdminDashboard();
      } else {
        await loadUserDashboard();
      }
    };

    const userBook = async (lotId) => {
      clearMessages();
      loading.value = true;
      try {
        const res = await fetch('/api/user/book', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ lot_id: lotId }),
        });
        const data = await res.json();
        if (!res.ok) {
          globalError.value = data.error || 'Could not book spot';
          return;
        }
        globalMessage.value = data.message || 'Spot booked';
        await loadUserDashboard();
      } catch (e) {
        globalError.value = 'Network error';
      } finally {
        loading.value = false;
      }
    };

    const userRelease = async (reservationId) => {
      clearMessages();
      loading.value = true;
      try {
        const res = await fetch('/api/user/release', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ reservation_id: reservationId }),
        });
        const data = await res.json();
        if (!res.ok) {
          globalError.value = data.error || 'Could not release spot';
          return;
        }
        globalMessage.value = data.message || 'Spot released';
        await loadUserDashboard();
      } catch (e) {
        globalError.value = 'Network error';
      } finally {
        loading.value = false;
      }
    };

    // ---- Admin lot management ----
    const createLot = async () => {
      clearMessages();
      if (!newLot.value.name || !newLot.value.address || !newLot.value.pincode) {
        globalError.value = 'Please fill all lot details.';
        return;
      }
      loading.value = true;
      try {
        const res = await fetch('/api/admin/lots', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(newLot.value),
        });
        const data = await res.json();
        if (!res.ok) {
          globalError.value = data.error || 'Failed to create lot';
          return;
        }
        globalMessage.value = 'Parking lot created.';
        newLot.value = {
          name: '',
          address: '',
          pincode: '',
          price_per_hour: '',
          max_spots: '',
        };
        await loadAdminDashboard();
      } catch (e) {
        globalError.value = 'Network error';
      } finally {
        loading.value = false;
      }
    };

    const prefillEditLot = (lot) => {
      editLot.value = {
        id: lot.id,
        name: lot.name,
        address: lot.address,
        pincode: lot.pincode,
        price_per_hour: lot.price_per_hour,
        max_spots: lot.max_spots,
      };
    };

    const updateLot = async () => {
      clearMessages();
      if (!editLot.value.id) return;
      loading.value = true;
      try {
        const res = await fetch(`/api/admin/lots/${editLot.value.id}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(editLot.value),
        });
        const data = await res.json();
        if (!res.ok) {
          globalError.value = data.error || 'Failed to update lot';
          return;
        }
        globalMessage.value = 'Parking lot updated.';
        editLot.value.id = null;
        await loadAdminDashboard();
      } catch (e) {
        globalError.value = 'Network error';
      } finally {
        loading.value = false;
      }
    };

    const deleteLot = async (id) => {
      clearMessages();
      loading.value = true;
      try {
        const res = await fetch(`/api/admin/lots/${id}`, {
          method: 'DELETE',
        });
        const data = await res.json();
        if (!res.ok) {
          globalError.value = data.error || 'Failed to delete lot';
          return;
        }
        globalMessage.value = data.message || 'Lot deleted.';
        await loadAdminDashboard();
      } catch (e) {
        globalError.value = 'Network error';
      } finally {
        loading.value = false;
      }
    };

    // ---- Admin summary ----
    const adminSummary = Vue.computed(() => {
      if (!adminDashboard.value) {
        return {
          totalRevenue: 0,
          occupied: 0,
          available: 0,
          activeUsers: 0,
          inactiveUsers: 0,
          monthlyRevenue: {},
        };
      }
      let totalRevenue = 0;
      const monthlyRevenue = {};
      (adminDashboard.value.reservations || []).forEach((r) => {
        if (r.cost != null && r.end_time) {
          totalRevenue += r.cost;
          const d = new Date(r.end_time);
          if (!isNaN(d)) {
            const key = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
            monthlyRevenue[key] = (monthlyRevenue[key] || 0) + r.cost;
          }
        }
      });

      let occupied = 0;
      let available = 0;
      (adminDashboard.value.lots || []).forEach((lot) => {
        occupied += lot.occupied_spots;
        available += lot.available_spots;
      });

      let activeUsers = 0;
      let inactiveUsers = 0;
      (adminDashboard.value.users || []).forEach((u) => {
        if (u.reservation_count > 0) activeUsers += 1;
        else inactiveUsers += 1;
      });

      return {
        totalRevenue,
        occupied,
        available,
        activeUsers,
        inactiveUsers,
        monthlyRevenue,
      };
    });

    // ---- Charts ----
    const rebuildAdminCharts = () => {
      if (!adminDashboard.value) return;

      // Monthly revenue (Dashboard tab)
      const monthly = adminSummary.value.monthlyRevenue;
      const labels = Object.keys(monthly).sort();
      const values = labels.map((k) => monthly[k]);

      const revenueCtx = document.getElementById('adminRevenueChart');
      if (revenueCtx) {
        if (adminRevenueChart) adminRevenueChart.destroy();
        adminRevenueChart = new Chart(revenueCtx, {
          type: 'line',
          data: {
            labels,
            datasets: [{
              label: 'Revenue',
              data: values,
              borderWidth: 2,
              tension: 0.35,
              fill: true,
            }],
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
              x: {
                ticks: { color: '#e5e7eb', font: { size: 12 } },
                grid: { color: 'rgba(55,65,81,0.6)' },
              },
              y: {
                ticks: { color: '#e5e7eb', font: { size: 12 } },
                grid: { color: 'rgba(31,41,55,0.6)' },
              },
            },
          },
        });
      }

      // Spot occupancy (Parking Lots tab)
      const occCtx = document.getElementById('adminOccupancyChart');
      if (occCtx) {
        if (adminOccupancyChart) adminOccupancyChart.destroy();
        adminOccupancyChart = new Chart(occCtx, {
          type: 'doughnut',
          data: {
            labels: ['Occupied', 'Available'],
            datasets: [{
              data: [adminSummary.value.occupied, adminSummary.value.available],
            }],
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
              legend: {
                position: 'bottom',
                labels: { color: '#e5e7eb', font: { size: 12 } },
              },
            },
            cutout: '65%',
          },
        });
      }

      // User status (Users tab)
      const userCtx = document.getElementById('adminUserStatusChart');
      if (userCtx) {
        if (adminUserStatusChart) adminUserStatusChart.destroy();
        adminUserStatusChart = new Chart(userCtx, {
          type: 'doughnut',
          data: {
            labels: ['Active', 'Inactive'],
            datasets: [{
              data: [adminSummary.value.activeUsers, adminSummary.value.inactiveUsers],
            }],
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
              legend: {
                position: 'bottom',
                labels: { color: '#e5e7eb', font: { size: 12 } },
              },
            },
            cutout: '65%',
          },
        });
      }
    };

    const rebuildUserCharts = () => {
      if (!userDashboard.value) return;
      const lotCounts = userDashboard.value.summary.lot_counts || {};
      const labels = Object.keys(lotCounts);
      const values = labels.map((k) => lotCounts[k]);

      const ctx = document.getElementById('userLotUsageChart');
      if (!ctx) return;
      if (userLotUsageChart) userLotUsageChart.destroy();
      userLotUsageChart = new Chart(ctx, {
        type: 'bar',
        data: {
          labels,
          datasets: [{
            label: 'Reservations',
            data: values,
          }],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: { legend: { display: false } },
          scales: {
            x: {
              ticks: { color: '#e5e7eb', font: { size: 12 } },
              grid: { display: false },
            },
            y: {
              ticks: { color: '#e5e7eb', font: { size: 12 } },
              grid: { color: 'rgba(31,41,55,0.6)' },
            },
          },
        },
      });
    };

    watch(adminDashboard, () => {
      setTimeout(rebuildAdminCharts, 0);
    });

    watch(userDashboard, () => {
      setTimeout(rebuildUserCharts, 0);
    });

    onMounted(fetchMe);

    const debugRunDailyReminders = async () => {
      clearMessages();
      loading.value = true;
      try {
        const res = await fetch('/debug/run_daily_reminders', { method: 'POST' });
        const data = await res.json();
        if (!res.ok) {
          globalError.value = data.error || 'Failed to queue daily reminders';
          return;
        }
        globalMessage.value = data.message || 'Daily reminders queued';
      } catch (e) {
        globalError.value = 'Network error';
      } finally {
        loading.value = false;
      }
    };

    const debugRunMonthlyReports = async () => {
      clearMessages();
      loading.value = true;
      try {
        const res = await fetch('/debug/run_monthly_reports', { method: 'POST' });
        const data = await res.json();
        if (!res.ok) {
          globalError.value = data.error || 'Failed to queue monthly reports';
          return;
        }
        globalMessage.value = data.message || 'Monthly reports queued';
      } catch (e) {
        globalError.value = 'Network error';
      } finally {
        loading.value = false;
      }
    };

    return {
      me,
      loginForm,
      registerForm,
      showRegister,
      globalError,
      globalMessage,
      loading,
      adminDashboard,
      userDashboard,
      adminTab,
      newLot,
      editLot,
      adminSummary,
      apiLogin,
      apiRegister,
      apiLogout,
      apiExportCsv,
      loadAdminDashboard,
      loadUserDashboard,
      refreshCurrent,
      userBook,
      userRelease,
      createLot,
      prefillEditLot,
      updateLot,
      deleteLot,
      formatDateTime,
      debugRunDailyReminders,
      debugRunMonthlyReports,
    };
  },
}).mount('#app');
