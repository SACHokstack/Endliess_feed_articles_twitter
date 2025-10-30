// Main Application Logic

class UnifiedApp {
    constructor() {
        this.stats = {};
        this.sources = {};
        this.scrapingTasks = {};

        this.initElements();
        this.initEventListeners();
        this.loadInitialData();
    }

    initElements() {
        // Scraping buttons
        this.scrapeTwitterBtn = document.getElementById('scrape-twitter-btn');

        // Progress elements
        this.twitterProgress = document.getElementById('twitter-progress');

        // Scraper status elements
        this.scraperStatus = document.getElementById('scraper-status');
        this.nextScrapeTime = document.getElementById('next-scrape-time');

        // Filter elements
        this.filterType = document.getElementById('filter-type');
        this.filterSource = document.getElementById('filter-source');
        this.filterStartDate = document.getElementById('filter-start-date');
        this.filterEndDate = document.getElementById('filter-end-date');
        this.filterSearch = document.getElementById('filter-search');
        this.applyFiltersBtn = document.getElementById('apply-filters-btn');
        this.clearFiltersBtn = document.getElementById('clear-filters-btn');

        // Twitter user management
        this.twitterUserInput = document.getElementById('twitter-user-input');
        this.addTwitterUserBtn = document.getElementById('add-twitter-user-btn');
        this.twitterUsersList = document.getElementById('twitter-users-list');

        // Other elements
        this.refreshFeedBtn = document.getElementById('refresh-feed-btn');
        this.notificationToast = document.getElementById('notification-toast');
        this.lightbox = document.getElementById('media-lightbox');
    }

    initEventListeners() {
        // Scraping
        if (this.scrapeTwitterBtn) {
            this.scrapeTwitterBtn.addEventListener('click', () => this.scrapeTwitter());
        }

        // Filters
        if (this.applyFiltersBtn) {
            this.applyFiltersBtn.addEventListener('click', () => this.applyFilters());
        }
        if (this.clearFiltersBtn) {
            this.clearFiltersBtn.addEventListener('click', () => this.clearFilters());
        }

        // Twitter user management
        if (this.addTwitterUserBtn) {
            this.addTwitterUserBtn.addEventListener('click', () => this.addTwitterUser());
        }
        if (this.twitterUserInput) {
            this.twitterUserInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') this.addTwitterUser();
            });
        }

        // Refresh
        if (this.refreshFeedBtn) {
            this.refreshFeedBtn.addEventListener('click', () => this.refreshFeed());
        }

        // Lightbox close
        if (this.lightbox) {
            this.lightbox.addEventListener('click', (e) => {
                if (e.target === this.lightbox || e.target.classList.contains('lightbox-overlay') || e.target.classList.contains('lightbox-close')) {
                    this.closeLightbox();
                }
            });
        }
    }

    async loadInitialData() {
        await Promise.all([
            this.loadStats(),
            this.loadSources(),
            this.loadTwitterUsers(),
            this.loadScraperStatus()
        ]);
    }

    async loadScraperStatus() {
        try {
            const response = await fetch('/api/scraper/status');
            const data = await response.json();

            if (data.success && data.status) {
                const status = data.status;

                if (status.enabled) {
                    if (this.scraperStatus) {
                        this.scraperStatus.textContent = '✓ Active';
                        this.scraperStatus.style.color = 'var(--accent-success)';
                    }

                    if (this.nextScrapeTime && status.next_run) {
                        const nextRun = new Date(status.next_run);
                        this.nextScrapeTime.textContent = this.formatDateTime(nextRun);
                    } else if (this.nextScrapeTime) {
                        this.nextScrapeTime.textContent = 'Starting soon...';
                    }
                } else {
                    if (this.scraperStatus) {
                        this.scraperStatus.textContent = '⚠ Inactive';
                        this.scraperStatus.style.color = 'var(--accent-warning)';
                    }
                }
            }
        } catch (error) {
            console.error('Error loading scraper status:', error);
        }
    }

    async loadStats() {
        try {
            const response = await fetch('/api/stats');
            const data = await response.json();

            if (data.success) {
                this.stats = data.stats;
                this.updateStatsDisplay();
            }
        } catch (error) {
            console.error('Error loading stats:', error);
        }
    }

    updateStatsDisplay() {
        // Update badges
        const totalItems = this.stats.combined?.total_items || 0;
        const totalArticles = this.stats.spine_articles?.total || 0;
        const totalTweets = this.stats.twitter?.total_tweets || 0;

        this.updateBadge('total-items-badge', totalItems);
        this.updateBadge('articles-badge', totalArticles);
        this.updateBadge('tweets-badge', totalTweets);

        // Update stats sidebar
        document.getElementById('stat-spine-sources').textContent = '3';
        document.getElementById('stat-twitter-users').textContent = this.stats.twitter?.total_users || 0;

        const lastUpdated = this.stats.combined?.last_updated;
        if (lastUpdated) {
            document.getElementById('stat-last-updated').textContent = this.formatDate(lastUpdated);
        }
    }

    updateBadge(badgeId, value) {
        const badge = document.getElementById(badgeId);
        if (badge) {
            const valueEl = badge.querySelector('.badge-value');
            if (valueEl) {
                valueEl.textContent = value.toLocaleString();
            }
        }
    }

    async loadSources() {
        try {
            const response = await fetch('/api/sources');
            const data = await response.json();

            if (data.success) {
                this.sources = data.sources;
                this.populateSourceFilter();
            }
        } catch (error) {
            console.error('Error loading sources:', error);
        }
    }

    populateSourceFilter() {
        if (!this.filterSource) return;

        // Clear existing options (except "All Sources")
        while (this.filterSource.options.length > 1) {
            this.filterSource.remove(1);
        }

        // Add spine sources
        if (this.sources.spine) {
            this.sources.spine.forEach(source => {
                const option = document.createElement('option');
                option.value = source.name;
                option.textContent = source.name;
                this.filterSource.appendChild(option);
            });
        }

        // Add Twitter sources
        if (this.sources.twitter) {
            this.sources.twitter.forEach(source => {
                const option = document.createElement('option');
                option.value = source.key;
                option.textContent = source.name;
                this.filterSource.appendChild(option);
            });
        }
    }

    async loadTwitterUsers() {
        if (!this.twitterUsersList) return;

        try {
            const response = await fetch('/api/sources');
            const data = await response.json();

            if (data.success && data.sources.twitter) {
                this.renderTwitterUsers(data.sources.twitter);
            }
        } catch (error) {
            console.error('Error loading Twitter users:', error);
        }
    }

    renderTwitterUsers(users) {
        if (!this.twitterUsersList) return;

        this.twitterUsersList.innerHTML = '';

        users.forEach(user => {
            const div = document.createElement('div');
            div.className = 'user-item';
            div.innerHTML = `
                <span>@${user.key}</span>
                <button class="user-remove-btn" onclick="app.removeTwitterUser('${user.key}')">×</button>
            `;
            this.twitterUsersList.appendChild(div);
        });
    }

    async addTwitterUser() {
        const username = this.twitterUserInput.value.trim().replace('@', '');

        if (!username) {
            this.showNotification('Please enter a username', 'error');
            return;
        }

        try {
            const response = await fetch('/api/twitter/users', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username })
            });

            const data = await response.json();

            if (data.success) {
                this.showNotification(`Added @${username}`, 'success');
                this.twitterUserInput.value = '';
                await this.loadTwitterUsers();
                await this.loadSources();
            } else {
                this.showNotification(data.result.message || 'Failed to add user', 'error');
            }
        } catch (error) {
            console.error('Error adding user:', error);
            this.showNotification('Failed to add user', 'error');
        }
    }

    async removeTwitterUser(username) {
        if (!confirm(`Remove @${username}?`)) return;

        try {
            const response = await fetch(`/api/twitter/users/${username}`, {
                method: 'DELETE'
            });

            const data = await response.json();

            if (data.success) {
                this.showNotification(`Removed @${username}`, 'success');
                await this.loadTwitterUsers();
                await this.loadSources();
            } else {
                this.showNotification('Failed to remove user', 'error');
            }
        } catch (error) {
            console.error('Error removing user:', error);
            this.showNotification('Failed to remove user', 'error');
        }
    }


    async scrapeTwitter() {
        const checkboxes = Array.from(document.querySelectorAll('.user-item'));
        const users = checkboxes.map(item => item.querySelector('span').textContent.replace('@', ''));
        const keyword = document.getElementById('twitter-keyword').value.trim();
        const limit = parseInt(document.getElementById('twitter-limit').value) || 50;

        if (users.length === 0 && !keyword) {
            this.showNotification('Please add users or enter a keyword', 'error');
            return;
        }

        try {
            this.scrapeTwitterBtn.disabled = true;
            this.twitterProgress.style.display = 'block';

            const response = await fetch('/api/scrape/twitter', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ users, keyword, limit })
            });

            const data = await response.json();

            if (data.success) {
                this.showNotification('Twitter scraping started!', 'success');
                this.scrapingTasks[data.task_id] = 'twitter';
                this.monitorTask(data.task_id);
            } else {
                throw new Error(data.error);
            }
        } catch (error) {
            console.error('Error starting Twitter scraping:', error);
            this.showNotification('Failed to start Twitter scraping', 'error');
            this.scrapeTwitterBtn.disabled = false;
            this.twitterProgress.style.display = 'none';
        }
    }

    async monitorTask(taskId) {
        const checkInterval = setInterval(async () => {
            try {
                const response = await fetch(`/api/tasks/${taskId}`);
                const data = await response.json();

                if (data.success) {
                    const task = data.task;

                    if (task.status === 'completed') {
                        clearInterval(checkInterval);
                        this.onTaskCompleted(taskId, task);
                    } else if (task.status === 'failed') {
                        clearInterval(checkInterval);
                        this.onTaskFailed(taskId, task);
                    }
                }
            } catch (error) {
                console.error('Error monitoring task:', error);
                clearInterval(checkInterval);
            }
        }, 2000);
    }

    onTaskCompleted(taskId, task) {
        const type = this.scrapingTasks[taskId];

        if (type === 'twitter') {
            this.scrapeTwitterBtn.disabled = false;
            this.twitterProgress.style.display = 'none';
            this.showNotification('Twitter scraping complete!', 'success');
        }

        delete this.scrapingTasks[taskId];
        this.refreshFeed();
        this.loadStats();
    }

    onTaskFailed(taskId, task) {
        const type = this.scrapingTasks[taskId];

        if (type === 'twitter') {
            this.scrapeTwitterBtn.disabled = false;
            this.twitterProgress.style.display = 'none';
        }

        this.showNotification('Scraping failed', 'error');
        delete this.scrapingTasks[taskId];
    }

    applyFilters() {
        const filters = {
            type: this.filterType.value,
            source: this.filterSource.value,
            startDate: this.filterStartDate.value,
            endDate: this.filterEndDate.value,
            search: this.filterSearch.value
        };

        if (window.feedManager) {
            window.feedManager.applyFilters(filters);
        }

        this.showNotification('Filters applied', 'info');
    }

    clearFilters() {
        this.filterType.value = 'both';
        this.filterSource.value = '';
        this.filterStartDate.value = '';
        this.filterEndDate.value = '';
        this.filterSearch.value = '';

        if (window.feedManager) {
            window.feedManager.clearFilters();
        }

        this.showNotification('Filters cleared', 'info');
    }

    refreshFeed() {
        if (window.feedManager) {
            // Force a fresh load by clearing any cached filters
            window.feedManager.clearFilters();
            window.feedManager.loadFeed(false);
        }
        this.loadStats();
    }

    openLightbox(imageUrl) {
        const lightboxImage = document.getElementById('lightbox-image');
        if (lightboxImage && this.lightbox) {
            lightboxImage.src = imageUrl;
            this.lightbox.style.display = 'block';
        }
    }

    closeLightbox() {
        if (this.lightbox) {
            this.lightbox.style.display = 'none';
        }
    }

    showNotification(message, type = 'info') {
        if (!this.notificationToast) return;

        const icon = type === 'success' ? '✓' :
                    type === 'error' ? '✗' :
                    type === 'warning' ? '⚠' : 'ℹ';

        const iconEl = this.notificationToast.querySelector('.notification-icon');
        const messageEl = this.notificationToast.querySelector('.notification-message');

        if (iconEl) iconEl.textContent = icon;
        if (messageEl) messageEl.textContent = message;

        this.notificationToast.classList.add('show');

        setTimeout(() => {
            this.notificationToast.classList.remove('show');
        }, 3000);
    }

    formatDate(dateStr) {
        const date = new Date(dateStr);
        return date.toLocaleString('en-US', {
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    }

    formatDateTime(date) {
        const now = new Date();
        const diffMs = date - now;
        const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
        const diffMins = Math.floor((diffMs % (1000 * 60 * 60)) / (1000 * 60));

        if (diffMs < 0) {
            return 'Running now...';
        } else if (diffHours < 1) {
            return `In ${diffMins} minutes`;
        } else if (diffHours < 24) {
            return `In ${diffHours} hours`;
        } else {
            return date.toLocaleString('en-US', {
                month: 'short',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit'
            });
        }
    }
}

// Initialize app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.app = new UnifiedApp();
});
