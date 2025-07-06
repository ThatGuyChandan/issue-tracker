<script>
  import { onMount } from 'svelte';
  import { user } from '$lib/userStore.js';
  import { browser } from '$app/environment';

  let issues = [];
  let loading = true;
  let error = '';
  let showCreateForm = false;
  let showNotification = false;
  let connectionStatus = 'disconnected'; // 'connected', 'disconnected', 'connecting', 'error'
  
  // Form data
  let newIssue = {
    title: '',
    description: '',
    severity: 'LOW'
  };

  // Editing state
  let editingId = null;
  let editTitle = '';
  let editDescription = '';
  let editSeverity = 'LOW';
  let editStatus = 'OPEN';
  let editError = '';

  // WebSocket connection
  let ws = null;

  // Notification sound
  let notificationSound = null;
  
  // Notification state
  let notificationMessage = '';
  let notificationType = 'info';

  onMount(() => {
    if (browser) {
      // Initialize notification sound
      notificationSound = new Audio('data:audio/wav;base64,UklGRnoGAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQoGAACBhYqFbF1fdJivrJBhNjVgodDbq2EcBj+a2/LDciUFLIHO8tiJNwgZaLvt559NEAxQp+PwtmMcBjiR1/LMeSwFJHfH8N2QQAoUXrTp66hVFApGn+DyvmwhBSuBzvLZiTYIG2m98OScTgwOUarm7blmGgU7k9n1unEiBC13yO/eizEIHWq+8+OWT');
      
      loadIssues();
      connectWebSocket();
    }
  });

  async function loadIssues() {
    try {
      const response = await fetch('/api/issues', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });
      
      if (response.ok) {
        issues = await response.json();
      } else {
        error = 'Failed to load issues';
      }
    } catch (err) {
      error = 'Failed to load issues';
    } finally {
      loading = false;
    }
  }

  function connectWebSocket() {
    if (!browser) return;
    
    const token = localStorage.getItem('token');
    if (!token || !$user) return;

    connectionStatus = 'connecting';
    const wsUrl = `ws://localhost:8000/api/ws?userid=${$user.id}&role=${$user.role}&email=${encodeURIComponent($user.email)}`;
    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      connectionStatus = 'connected';
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        handleWebSocketMessage(data);
      } catch (e) {
        // Silently handle WebSocket message parsing errors
      }
    };

    ws.onclose = () => {
      connectionStatus = 'disconnected';
      // Reconnect after 5 seconds
      setTimeout(connectWebSocket, 5000);
    };

    ws.onerror = () => {
      connectionStatus = 'error';
    };
  }

  function handleWebSocketMessage(data) {
    // Handle different types of notifications
    if (data.type === 'issue_created' || data.type === 'issue_updated' || data.type === 'issue_deleted') {
      showNotification = true;
      
      // Set notification message based on type
      if (data.type === 'issue_created') {
        notificationType = 'success';
        notificationMessage = `New issue created: "${data.title}" by ${data.reporter_email}`;
      } else if (data.type === 'issue_updated') {
        notificationType = 'info';
        notificationMessage = `Issue updated: "${data.title}" by ${data.updated_by_email}`;
      } else if (data.type === 'issue_deleted') {
        notificationType = 'warning';
        notificationMessage = `Issue deleted: "${data.title}" by ${data.deleted_by_email}`;
      }
      
      if (notificationSound) {
        notificationSound.play().catch(() => {});
      }
      
      // Hide notification after 6 seconds
      setTimeout(() => {
        showNotification = false;
        notificationMessage = '';
      }, 6000);
      
      // Reload issues to get latest data
      loadIssues();
    }
  }

  async function createIssue() {
    try {
      const response = await fetch('/api/issues', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify(newIssue)
      });

      if (response.ok) {
        const issue = await response.json();
        issues.unshift(issue);
        newIssue = { title: '', description: '', severity: 'LOW' };
        showCreateForm = false;
      } else {
        error = 'Failed to create issue';
      }
    } catch (err) {
      error = 'Failed to create issue';
    }
  }

  function startEdit(issue) {
    editingId = issue.id;
    editTitle = issue.title;
    editDescription = issue.description;
    editSeverity = issue.severity;
    editStatus = issue.status;
    editError = '';
  }

  function cancelEdit() {
    editingId = null;
    editTitle = '';
    editDescription = '';
    editSeverity = 'LOW';
    editStatus = 'OPEN';
    editError = '';
  }

  async function saveEdit(issue) {
    try {
      const updates = {};
      if (editTitle !== issue.title) updates.title = editTitle;
      if (editDescription !== issue.description) updates.description = editDescription;
      if (editSeverity !== issue.severity) updates.severity = editSeverity;
      if (editStatus !== issue.status) updates.status = editStatus;

      const response = await fetch(`/api/issues/${issue.id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify(updates)
      });

      if (response.ok) {
        const updatedIssue = await response.json();
        issues = issues.map(i => i.id === issue.id ? updatedIssue : i);
        editingId = null;
      } else {
        const errorData = await response.json();
        editError = errorData.detail || 'Failed to update issue';
      }
    } catch (err) {
      editError = 'Failed to update issue';
    }
  }

  async function deleteIssue(issueId) {
    if (!confirm('Are you sure you want to delete this issue?')) return;
    
    try {
      const response = await fetch(`/api/issues/${issueId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });

      if (response.ok) {
        issues = issues.filter(issue => issue.id !== issueId);
      } else {
        error = 'Failed to delete issue';
      }
    } catch (err) {
      error = 'Failed to delete issue';
    }
  }

  function getSeverityColor(severity) {
    switch (severity) {
      case 'CRITICAL': return 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200';
      case 'HIGH': return 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200';
      case 'MEDIUM': return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200';
      case 'LOW': return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200';
      default: return 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200';
    }
  }

  function getStatusColor(status) {
    switch (status) {
      case 'OPEN': return 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200';
      case 'TRIAGED': return 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200';
      case 'IN_PROGRESS': return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200';
      case 'DONE': return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200';
      default: return 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200';
    }
  }
</script>

<!-- Notification Popup -->
{#if showNotification}
  <div class="fixed top-4 right-4 z-50">
    <div class="bg-white dark:bg-gray-800 rounded-lg shadow-xl border-l-4 {notificationType === 'success' ? 'border-green-500 bg-green-50 dark:bg-green-900/20' : notificationType === 'warning' ? 'border-yellow-500 bg-yellow-50 dark:bg-yellow-900/20' : 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'} p-4 max-w-sm transform transition-all duration-300 ease-in-out animate-slide-in">
      <div class="flex items-start">
        <div class="flex-shrink-0">
          {#if notificationType === 'success'}
            <svg class="h-5 w-5 text-green-400" fill="currentColor" viewBox="0 0 20 20">
              <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"></path>
            </svg>
          {:else if notificationType === 'warning'}
            <svg class="h-5 w-5 text-yellow-400" fill="currentColor" viewBox="0 0 20 20">
              <path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd"></path>
            </svg>
          {:else}
            <svg class="h-5 w-5 text-blue-400" fill="currentColor" viewBox="0 0 20 20">
              <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd"></path>
            </svg>
          {/if}
        </div>
        <div class="ml-3 flex-1">
          <p class="text-sm font-medium text-gray-900 dark:text-gray-100">
            {notificationType === 'success' ? 'Issue Created' : notificationType === 'warning' ? 'Issue Deleted' : 'Issue Updated'}
          </p>
          <p class="text-xs text-gray-600 dark:text-gray-400 mt-1">{notificationMessage}</p>
        </div>
        <div class="ml-4 flex-shrink-0">
          <button 
            class="text-gray-400 hover:text-gray-600 dark:text-gray-500 dark:hover:text-gray-300 transition-colors duration-200"
            on:click={() => { showNotification = false; notificationMessage = ''; }}
            aria-label="Close notification"
          >
            <svg class="h-4 w-4" fill="currentColor" viewBox="0 0 20 20">
              <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd"></path>
            </svg>
          </button>
        </div>
      </div>
    </div>
  </div>
{/if}

<style>
  @keyframes slide-in {
    from {
      opacity: 0;
      transform: translateX(100%);
    }
    to {
      opacity: 1;
      transform: translateX(0);
    }
  }
  
  .animate-slide-in {
    animation: slide-in 0.3s ease-out;
  }
</style>

<div class="min-h-screen bg-gray-50 dark:bg-gray-900 transition-colors duration-200">
  <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
    <div class="space-y-8">
      <!-- Header -->
      <div class="flex items-center justify-between">
        <div>
          <h1 class="text-3xl font-bold text-gray-900 dark:text-white">Issues</h1>
          <p class="text-gray-600 dark:text-gray-400 mt-1">Track and manage issues with real-time updates</p>
        </div>
        <div class="flex items-center space-x-4">
          <!-- Connection Status Indicator -->
          <div class="flex items-center space-x-2">
            <div class="flex items-center space-x-1">
              <div class="w-2 h-2 rounded-full {connectionStatus === 'connected' ? 'bg-green-500' : connectionStatus === 'connecting' ? 'bg-yellow-500' : connectionStatus === 'error' ? 'bg-red-500' : 'bg-gray-400'}"></div>
              <span class="text-xs text-gray-600 dark:text-gray-300">
                {connectionStatus === 'connected' ? 'Real-time connected' : 
                 connectionStatus === 'connecting' ? 'Connecting...' : 
                 connectionStatus === 'error' ? 'Connection error' : 
                 'Disconnected'}
              </span>
            </div>
          </div>
          <div class="text-sm text-gray-600 dark:text-gray-300">
            {issues.length} issue{issues.length !== 1 ? 's' : ''}
          </div>
        </div>
      </div>

      <!-- Create Issue Form -->
      <div class="bg-white dark:bg-gray-800 rounded-xl shadow-lg border border-gray-100 dark:border-gray-700 p-6">
        <h2 class="text-xl font-semibold text-gray-900 dark:text-white mb-4">Create New Issue</h2>
        
        <form on:submit|preventDefault={createIssue} class="space-y-4">
          <div class="grid md:grid-cols-2 gap-4">
            <div>
              <label for="title" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Title
              </label>
              <input 
                id="title"
                class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white dark:placeholder-gray-400 transition-colors duration-200" 
                placeholder="Enter issue title" 
                bind:value={newIssue.title} 
                required 
              />
            </div>
            
            <div>
              <label for="severity" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Severity
              </label>
              <select 
                id="severity"
                class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white transition-colors duration-200" 
                bind:value={newIssue.severity}
              >
                <option value="LOW">Low</option>
                <option value="MEDIUM">Medium</option>
                <option value="HIGH">High</option>
                <option value="CRITICAL">Critical</option>
              </select>
            </div>
          </div>
          
          <div>
            <label for="description" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Description
            </label>
            <textarea 
              id="description"
              class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white dark:placeholder-gray-400 transition-colors duration-200" 
              placeholder="Describe the issue" 
              bind:value={newIssue.description} 
              rows="4"
              required
            ></textarea>
          </div>
          
          <button 
            type="submit" 
            disabled={loading}
            class="bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white px-6 py-2 rounded-lg font-medium transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2"
          >
            {#if loading}
              <svg class="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              <span>Creating...</span>
            {:else}
              <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6"></path>
              </svg>
              <span>Create Issue</span>
            {/if}
          </button>
        </form>
      </div>

      <!-- Issues List -->
      <div class="space-y-4">
        {#each issues as issue}
          <div class="bg-white dark:bg-gray-800 rounded-xl shadow-lg border border-gray-100 dark:border-gray-700 p-6">
            <div class="flex justify-between items-start mb-4">
              <div class="flex-1">
                <div class="flex items-center space-x-3 mb-2">
                  <h3 class="text-lg font-semibold text-gray-900 dark:text-white">{issue.title}</h3>
                  <span class={`px-2 py-1 rounded-full text-xs font-medium ${getSeverityColor(issue.severity)}`}>
                    {issue.severity}
                  </span>
                  <span class={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(issue.status)}`}>
                    {issue.status.replace('_', ' ')}
                  </span>
                </div>
                <p class="text-sm text-gray-600 dark:text-gray-300">
                  Created by {issue.reporter_email} • {new Date(issue.created_at).toLocaleDateString()}
                </p>
              </div>
              
              {#if $user && ($user.role === 'ADMIN' || $user.role === 'MAINTAINER' || ($user.role === 'REPORTER' && issue.reporter_id == $user.id))}
                <div class="flex items-center space-x-2">
                  {#if editingId === issue.id}
                    <button 
                      class="text-green-600 hover:text-green-700 dark:text-green-400 dark:hover:text-green-300 font-medium text-sm flex items-center space-x-1"
                      on:click={() => saveEdit(issue)}
                    >
                      <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
                      </svg>
                      <span>Save</span>
                    </button>
                    <button 
                      class="text-gray-600 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300 font-medium text-sm flex items-center space-x-1"
                      on:click={cancelEdit}
                    >
                      <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                      </svg>
                      <span>Cancel</span>
                    </button>
                  {:else}
                    <button 
                      class="text-blue-600 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300 font-medium text-sm flex items-center space-x-1"
                      on:click={() => startEdit(issue)}
                    >
                      <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"></path>
                      </svg>
                      <span>Edit</span>
                    </button>
                    {#if $user.role === 'ADMIN'}
                      <button 
                        class="text-red-600 hover:text-red-700 dark:text-red-400 dark:hover:text-red-300 font-medium text-sm flex items-center space-x-1"
                        on:click={() => deleteIssue(issue.id)}
                      >
                        <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path>
                        </svg>
                        <span>Delete</span>
                      </button>
                    {/if}
                  {/if}
                </div>
              {/if}
            </div>

            {#if editingId === issue.id}
              <div class="space-y-4 border-t border-gray-200 dark:border-gray-700 pt-4">
                <input 
                  class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white transition-colors duration-200" 
                  bind:value={editTitle} 
                  placeholder="Issue title"
                />
                <textarea 
                  class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white transition-colors duration-200" 
                  bind:value={editDescription}
                  rows="3"
                  placeholder="Issue description"
                ></textarea>
                <div class="grid md:grid-cols-2 gap-4">
                  <select 
                    class="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white transition-colors duration-200" 
                    bind:value={editSeverity}
                  >
                    <option value="LOW">Low</option>
                    <option value="MEDIUM">Medium</option>
                    <option value="HIGH">High</option>
                    <option value="CRITICAL">Critical</option>
                  </select>
                  {#if $user.role === 'MAINTAINER' || $user.role === 'ADMIN'}
                    <select 
                      class="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white transition-colors duration-200" 
                      bind:value={editStatus}
                    >
                      <option value="OPEN">Open</option>
                      <option value="TRIAGED">Triaged</option>
                      <option value="IN_PROGRESS">In Progress</option>
                      <option value="DONE">Done</option>
                    </select>
                  {/if}
                </div>
                {#if editError}
                  <div class="text-red-600 dark:text-red-400 text-sm">{editError}</div>
                {/if}
              </div>
            {:else}
              <div class="prose prose-sm max-w-none dark:prose-invert">
                <p class="text-gray-700 dark:text-gray-200">{issue.description}</p>
              </div>
            {/if}
          </div>
        {/each}
      </div>

      {#if issues.length === 0}
        <div class="text-center py-12">
          <svg class="mx-auto h-12 w-12 text-gray-400 dark:text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
          </svg>
          <h3 class="mt-2 text-sm font-medium text-gray-900 dark:text-white">No issues</h3>
          <p class="mt-1 text-sm text-gray-600 dark:text-gray-300">Get started by creating a new issue.</p>
        </div>
      {/if}
    </div>
  </div>
</div> 