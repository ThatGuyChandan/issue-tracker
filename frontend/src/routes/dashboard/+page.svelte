<script>
  import { user } from '$lib/userStore.js';
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { Chart, registerables } from 'chart.js';
  import { getToken, getUser } from '$lib/auth.js';
  import io from 'socket.io-client';
  
  Chart.register(...registerables);
  
  let unsubscribe;
  onMount(() => {
    unsubscribe = user.subscribe(u => {
      if (!u) goto('/login');
    });
  });
  
  let stats = {
    totalIssues: 0,
    openIssues: 0,
    inProgressIssues: 0,
    completedIssues: 0,
    criticalIssues: 0,
    highPriorityIssues: 0
  };
  let recentIssues = [];
  let loading = true;
  let chartCanvas;
  let chart;
  let socket;

  async function fetchDashboardData() {
    try {
      const [statsRes, issuesRes] = await Promise.all([
        fetch('/api/stats/dashboard', {
          headers: { Authorization: `Bearer ${getToken()}` }
        }),
        fetch('/api/issues', {
          headers: { Authorization: `Bearer ${getToken()}` }
        })
      ]);

      if (issuesRes.ok) {
        const issues = await issuesRes.json();
        recentIssues = issues.slice(0, 5); // Get latest 5 issues
        
        // Calculate stats
        stats = {
          totalIssues: issues.length,
          openIssues: issues.filter(i => i.status === 'OPEN').length,
          inProgressIssues: issues.filter(i => i.status === 'IN_PROGRESS').length,
          completedIssues: issues.filter(i => i.status === 'DONE').length,
          criticalIssues: issues.filter(i => i.severity === 'CRITICAL').length,
          highPriorityIssues: issues.filter(i => i.severity === 'HIGH').length
        };
        
        // Create chart data after a small delay to ensure canvas is ready
        setTimeout(() => {
          createChart(issues);
        }, 200);
      }
    } catch (err) {
      // Handle error silently
    } finally {
      loading = false;
    }
  }

  function createChart(issues) {
    if (chart) {
      chart.destroy();
    }
    
    // Wait for the canvas to be available
    if (!chartCanvas) {
      return;
    }
    
    // Filter open issues and count by severity
    const openIssues = issues.filter(i => i.status === 'OPEN');
    const severityCounts = {
      'LOW': 0,
      'MEDIUM': 0,
      'HIGH': 0,
      'CRITICAL': 0
    };
    
    openIssues.forEach(issue => {
      severityCounts[issue.severity]++;
    });
    
    try {
      const ctx = chartCanvas.getContext('2d');
      chart = new Chart(ctx, {
        type: 'bar',
        data: {
          labels: Object.keys(severityCounts),
          datasets: [{
            label: 'Open Issues by Severity',
            data: Object.values(severityCounts),
            backgroundColor: [
              'rgba(34, 197, 94, 0.8)',   // Green for LOW
              'rgba(251, 191, 36, 0.8)',  // Yellow for MEDIUM
              'rgba(249, 115, 22, 0.8)',  // Orange for HIGH
              'rgba(239, 68, 68, 0.8)'    // Red for CRITICAL
            ],
            borderColor: [
              'rgb(34, 197, 94)',
              'rgb(251, 191, 36)',
              'rgb(249, 115, 22)',
              'rgb(239, 68, 68)'
            ],
            borderWidth: 1
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: {
              display: false
            },
            title: {
              display: true,
              text: 'Open Issues by Severity',
              font: {
                size: 16,
                weight: 'bold'
              }
            }
          },
          scales: {
            y: {
              beginAtZero: true,
              ticks: {
                stepSize: 1
              }
            }
          }
        }
      });
    } catch (error) {
      // Handle chart creation error silently
    }
  }

  function getStatusColor(status) {
    switch (status) {
      case 'OPEN': return 'bg-blue-100 text-blue-800';
      case 'TRIAGED': return 'bg-purple-100 text-purple-800';
      case 'IN_PROGRESS': return 'bg-yellow-100 text-yellow-800';
      case 'DONE': return 'bg-green-100 text-green-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  }

  function getSeverityColor(severity) {
    switch (severity) {
      case 'LOW': return 'bg-green-100 text-green-800';
      case 'MEDIUM': return 'bg-yellow-100 text-yellow-800';
      case 'HIGH': return 'bg-orange-100 text-orange-800';
      case 'CRITICAL': return 'bg-red-100 text-red-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  }

  onMount(() => {
    fetchDashboardData();
    
    // Connect to WebSocket for real-time updates
    const currentUser = getUser();
    if (currentUser && currentUser.id) {
      socket = io('http://localhost:8000', {
        path: '/notification/ws',
        query: {
          user_id: currentUser.id
        },
        transports: ['websocket', 'polling']
      });
      
      socket.on('connect', () => {
        // WebSocket connected
      });
      
      socket.on('new_issue', (data) => {
        // Fetch updated data when we receive an update
        fetchDashboardData();
      });
      
      socket.on('connect_error', (error) => {
        // Handle connection error silently
      });
    }
    
    return () => {
      if (socket) {
        socket.disconnect();
      }
    };
  });

  // Watch for chartCanvas changes and create chart when available
  $: if (chartCanvas && !chart) {
    // Small delay to ensure canvas is fully rendered
    setTimeout(() => {
      if (chartCanvas) {
        createChart(recentIssues);
      }
    }, 100);
  }
</script>

<div class="space-y-8">
  <!-- Header -->
  <div>
    <h1 class="text-3xl font-bold text-gray-900">Dashboard</h1>
    <p class="text-gray-600 mt-1">Overview of your issue tracking system</p>
  </div>

  {#if loading}
    <div class="flex items-center justify-center py-12">
      <svg class="animate-spin h-8 w-8 text-blue-600" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
      </svg>
    </div>
  {:else}
    <!-- Stats Cards -->
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      <!-- Total Issues -->
      <div class="bg-white rounded-xl shadow-lg border border-gray-100 p-6">
        <div class="flex items-center">
          <div class="flex-shrink-0">
            <div class="w-8 h-8 bg-blue-100 rounded-lg flex items-center justify-center">
              <svg class="w-5 h-5 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
              </svg>
            </div>
          </div>
          <div class="ml-4">
            <p class="text-sm font-medium text-gray-600">Total Issues</p>
            <p class="text-2xl font-bold text-gray-900">{stats.totalIssues}</p>
          </div>
        </div>
      </div>

      <!-- Open Issues -->
      <div class="bg-white rounded-xl shadow-lg border border-gray-100 p-6">
        <div class="flex items-center">
          <div class="flex-shrink-0">
            <div class="w-8 h-8 bg-yellow-100 rounded-lg flex items-center justify-center">
              <svg class="w-5 h-5 text-yellow-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"></path>
              </svg>
            </div>
          </div>
          <div class="ml-4">
            <p class="text-sm font-medium text-gray-600">Open Issues</p>
            <p class="text-2xl font-bold text-gray-900">{stats.openIssues}</p>
          </div>
        </div>
      </div>

      <!-- In Progress -->
      <div class="bg-white rounded-xl shadow-lg border border-gray-100 p-6">
        <div class="flex items-center">
          <div class="flex-shrink-0">
            <div class="w-8 h-8 bg-purple-100 rounded-lg flex items-center justify-center">
              <svg class="w-5 h-5 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path>
              </svg>
            </div>
          </div>
          <div class="ml-4">
            <p class="text-sm font-medium text-gray-600">In Progress</p>
            <p class="text-2xl font-bold text-gray-900">{stats.inProgressIssues}</p>
          </div>
        </div>
      </div>

      <!-- Completed -->
      <div class="bg-white rounded-xl shadow-lg border border-gray-100 p-6">
        <div class="flex items-center">
          <div class="flex-shrink-0">
            <div class="w-8 h-8 bg-green-100 rounded-lg flex items-center justify-center">
              <svg class="w-5 h-5 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path>
              </svg>
            </div>
          </div>
          <div class="ml-4">
            <p class="text-sm font-medium text-gray-600">Completed</p>
            <p class="text-2xl font-bold text-gray-900">{stats.completedIssues}</p>
          </div>
        </div>
      </div>

      <!-- Critical Issues -->
      <div class="bg-white rounded-xl shadow-lg border border-gray-100 p-6">
        <div class="flex items-center">
          <div class="flex-shrink-0">
            <div class="w-8 h-8 bg-red-100 rounded-lg flex items-center justify-center">
              <svg class="w-5 h-5 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z"></path>
              </svg>
            </div>
          </div>
          <div class="ml-4">
            <p class="text-sm font-medium text-gray-600">Critical Issues</p>
            <p class="text-2xl font-bold text-gray-900">{stats.criticalIssues}</p>
          </div>
        </div>
      </div>

      <!-- High Priority -->
      <div class="bg-white rounded-xl shadow-lg border border-gray-100 p-6">
        <div class="flex items-center">
          <div class="flex-shrink-0">
            <div class="w-8 h-8 bg-orange-100 rounded-lg flex items-center justify-center">
              <svg class="w-5 h-5 text-orange-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path>
              </svg>
            </div>
          </div>
          <div class="ml-4">
            <p class="text-sm font-medium text-gray-600">High Priority</p>
            <p class="text-2xl font-bold text-gray-900">{stats.highPriorityIssues}</p>
          </div>
        </div>
      </div>
    </div>

    <!-- Chart Section -->
    <div class="bg-white rounded-xl shadow-lg border border-gray-100 p-6">
      <h2 class="text-xl font-semibold text-gray-900 mb-6">Issue Severity Chart</h2>
      <div class="h-80">
        <canvas bind:this={chartCanvas}></canvas>
      </div>
    </div>

    <!-- Recent Issues -->
    <div class="bg-white rounded-xl shadow-lg border border-gray-100 p-6">
      <div class="flex items-center justify-between mb-6">
        <h2 class="text-xl font-semibold text-gray-900">Recent Issues</h2>
        <a href="/issues" class="text-blue-600 hover:text-blue-700 font-medium text-sm">
          View all issues →
        </a>
      </div>

      {#if recentIssues.length > 0}
        <div class="space-y-4">
          {#each recentIssues as issue}
            <div class="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
              <div class="flex-1">
                <h3 class="text-sm font-medium text-gray-900">{issue.title}</h3>
                <p class="text-sm text-gray-500">
                  Created by {issue.reporter_email} • {new Date(issue.created_at).toLocaleDateString()}
                </p>
              </div>
              <div class="flex items-center space-x-2">
                <span class={`px-2 py-1 rounded-full text-xs font-medium ${getSeverityColor(issue.severity)}`}>
                  {issue.severity}
                </span>
                <span class={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(issue.status)}`}>
                  {issue.status.replace('_', ' ')}
                </span>
              </div>
            </div>
          {/each}
        </div>
      {:else}
        <div class="text-center py-8">
          <svg class="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
          </svg>
          <h3 class="mt-2 text-sm font-medium text-gray-900">No issues yet</h3>
          <p class="mt-1 text-sm text-gray-500">Get started by creating your first issue.</p>
          <div class="mt-6">
            <a href="/issues" class="inline-flex items-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700">
              Create Issue
            </a>
          </div>
        </div>
      {/if}
    </div>

    <!-- Quick Actions -->
    <div class="bg-white rounded-xl shadow-lg border border-gray-100 p-6">
      <h2 class="text-xl font-semibold text-gray-900 mb-6">Quick Actions</h2>
      <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
        <a href="/issues" class="flex items-center p-4 border border-gray-200 rounded-lg hover:border-blue-300 hover:bg-blue-50 transition-colors duration-200">
          <div class="flex-shrink-0">
            <div class="w-8 h-8 bg-blue-100 rounded-lg flex items-center justify-center">
              <svg class="w-5 h-5 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6"></path>
              </svg>
            </div>
          </div>
          <div class="ml-4">
            <p class="text-sm font-medium text-gray-900">Create Issue</p>
            <p class="text-xs text-gray-500">Add a new issue to track</p>
          </div>
        </a>

        <a href="/issues" class="flex items-center p-4 border border-gray-200 rounded-lg hover:border-green-300 hover:bg-green-50 transition-colors duration-200">
          <div class="flex-shrink-0">
            <div class="w-8 h-8 bg-green-100 rounded-lg flex items-center justify-center">
              <svg class="w-5 h-5 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v10a2 2 0 002 2h8a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"></path>
              </svg>
            </div>
          </div>
          <div class="ml-4">
            <p class="text-sm font-medium text-gray-900">View Issues</p>
            <p class="text-xs text-gray-500">Browse all issues</p>
          </div>
        </a>

        <a href="/register" class="flex items-center p-4 border border-gray-200 rounded-lg hover:border-purple-300 hover:bg-purple-50 transition-colors duration-200">
          <div class="flex-shrink-0">
            <div class="w-8 h-8 bg-purple-100 rounded-lg flex items-center justify-center">
              <svg class="w-5 h-5 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M18 9v3m0 0v3m0-3h3m-3 0h-3m-2-5a4 4 0 11-8 0 4 4 0 018 0zM3 20a6 6 0 0112 0v1H3v-1z"></path>
              </svg>
            </div>
          </div>
          <div class="ml-4">
            <p class="text-sm font-medium text-gray-900">Invite Team</p>
            <p class="text-xs text-gray-500">Add team members</p>
          </div>
        </a>
      </div>
    </div>
  {/if}
</div> 