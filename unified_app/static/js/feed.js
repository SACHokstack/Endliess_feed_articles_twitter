// Feed Management

class FeedManager {
    constructor() {
        this.feedContainer = document.getElementById('feed-container');
        this.loadingEl = document.getElementById('feed-loading');
        this.emptyEl = document.getElementById('feed-empty');
        this.loadMoreContainer = document.getElementById('load-more-container');
        this.loadMoreBtn = document.getElementById('load-more-btn');

        // Unlimited scroll - load all content at once
        this.limit = 10000; // Very high limit to load everything
        this.isLoading = false;

        this.filters = {
            type: 'both',
            source: '',
            startDate: '',
            endDate: '',
            search: ''
        };

        this.init();
    }

    init() {
        // Load initial feed (all content at once)
        this.loadFeed();

        // Hide load more container since we load everything at once
        if (this.loadMoreContainer) {
            this.loadMoreContainer.style.display = 'none';
        }
    }


    async loadFeed(append = false) {
        if (this.isLoading) return;

        this.isLoading = true;

        // Always load from the beginning for unlimited content
        this.showLoading();

        try {
            const url = this.buildFeedUrl();

            const response = await fetch(url);
            const data = await response.json();

            if (data.success) {
                this.renderFeed(data.feed);

                // Show empty state if no items
                if (data.feed.length === 0) {
                    this.showEmpty();
                }
            } else {
                throw new Error(data.error || 'Failed to load feed');
            }
        } catch (error) {
            console.error('Error loading feed:', error);
            this.showNotification('Failed to load feed', 'error');
        } finally {
            this.isLoading = false;
            this.hideLoading();
        }
    }

    buildFeedUrl() {
        const params = new URLSearchParams({
            limit: this.limit, // High limit to load all content
            type: this.filters.type
        });

        if (this.filters.source) params.append('source', this.filters.source);
        if (this.filters.startDate) params.append('start_date', this.filters.startDate);
        if (this.filters.endDate) params.append('end_date', this.filters.endDate);
        if (this.filters.search) params.append('search', this.filters.search);

        return `/api/feed?${params.toString()}`;
    }

    renderFeed(items) {
        // Clear existing items except loading/empty states
        const existingItems = this.feedContainer.querySelectorAll('.feed-item');
        existingItems.forEach(item => item.remove());

        if (items.length === 0) {
            this.showEmpty();
            return;
        }

        this.hideEmpty();
        items.forEach(item => this.appendFeedItem(item));
    }

    appendFeedItems(items) {
        this.hideEmpty();
        items.forEach(item => this.appendFeedItem(item));
    }

    appendFeedItem(item) {
        const itemEl = this.createFeedItem(item);

        // Insert before loading/empty elements
        if (this.loadingEl.nextSibling) {
            this.feedContainer.insertBefore(itemEl, this.loadingEl.nextSibling);
        } else {
            this.feedContainer.appendChild(itemEl);
        }
    }

    createFeedItem(item) {
        const div = document.createElement('div');
        div.className = `feed-item ${item.type}-card`;
        div.setAttribute('data-id', item.id);
        div.setAttribute('data-type', item.type);

        if (item.type === 'article') {
            div.innerHTML = this.createArticleCard(item);
        } else if (item.type === 'tweet') {
            div.innerHTML = this.createTweetCard(item);
        }

        return div;
    }

    createArticleCard(item) {
        const financialTags = item.metadata.financial_mentions?.map(mention =>
            `<span class="metadata-tag financial">${mention}</span>`
        ).join('') || '';

        const procedureTags = item.metadata.spine_procedures?.slice(0, 5).map(proc =>
            `<span class="metadata-tag procedure">${proc}</span>`
        ).join('') || '';

        return `
            <div class="card-header">
                <span class="card-type-badge article">📰 Article</span>
                <span class="card-date">${this.formatDate(item.date)}</span>
            </div>
            <div class="card-source">
                <div class="source-avatar">${this.getInitials(item.source.name)}</div>
                <div class="source-info">
                    <div class="source-name">${item.source.name}</div>
                    <div class="source-type">${item.url}</div>
                </div>
            </div>
            <h3 class="card-title">
                <a href="/article?url=${encodeURIComponent(item.id)}" class="title-link">${item.content.title}</a>
            </h3>
            <p class="card-content">${item.content.summary}</p>
            ${financialTags || procedureTags ? `
            <div class="card-metadata">
                ${financialTags ? `
                <div class="metadata-section">
                    <div class="metadata-label">Financial Mentions</div>
                    <div class="metadata-tags">${financialTags}</div>
                </div>
                ` : ''}
                ${procedureTags ? `
                <div class="metadata-section">
                    <div class="metadata-label">Procedures</div>
                    <div class="metadata-tags">${procedureTags}</div>
                </div>
                ` : ''}
            </div>
            ` : ''}
            <div class="card-footer">
                <div class="card-actions">
                    <span class="metadata-tag">${item.metadata.content_length} chars</span>
                </div>
            </div>
        `;
    }

    createTweetCard(item) {
        const mediaHtml = item.media && item.media.length > 0 ?
            this.createMediaGrid(item.media) : '';

        const retweetHtml = item.metadata.retweet_info?.is_retweet ? `
            <div class="retweet-info">
                <span class="retweet-icon">🔄</span>
                <span class="retweet-text">
                    Retweeted by <span class="retweet-author">@${item.metadata.retweet_info.retweet_author}</span>
                </span>
            </div>
        ` : '';

        return `
            <div class="card-header">
                <span class="card-type-badge tweet">🐦 Tweet</span>
                <span class="card-date">${this.formatDate(item.date)}</span>
            </div>
            <div class="card-source">
                <div class="source-avatar">${this.getInitials(item.source.name)}</div>
                <div class="source-info">
                    <div class="source-name">${item.source.name}</div>
                    <div class="source-type">Twitter</div>
                </div>
            </div>
            <div class="card-content">${this.escapeHtml(item.content.text)}</div>
            ${mediaHtml}
            ${retweetHtml}
            <div class="card-footer">
                <div class="card-actions">
                    <span class="metadata-tag">${item.metadata.tweet_type}</span>
                </div>
                <a href="${item.url}" target="_blank" class="card-link">
                    View on Twitter →
                </a>
            </div>
        `;
    }

    createMediaGrid(media) {
        const gridClass = media.length === 1 ? 'single' :
                         media.length === 2 ? 'double' :
                         media.length === 3 ? 'triple' : 'quad';

        const mediaItems = media.slice(0, 4).map(item => {
            if (item.type === 'video') {
                return `
                    <div class="media-item" onclick="window.open('${item.url}', '_blank')">
                        <video src="${item.url}" preload="metadata"></video>
                        <div class="media-play-icon">▶</div>
                    </div>
                `;
            } else {
                return `
                    <div class="media-item" onclick="app.openLightbox('${item.url}')">
                        <img src="${item.url}" alt="Media" loading="lazy">
                    </div>
                `;
            }
        }).join('');

        return `
            <div class="card-media">
                <div class="media-grid ${gridClass}">
                    ${mediaItems}
                </div>
            </div>
        `;
    }

    // Removed loadMore and updateLoadMoreButton methods since we load everything at once

    applyFilters(filters) {
        this.filters = { ...this.filters, ...filters };
        this.loadFeed(false);
    }

    clearFilters() {
        this.filters = {
            type: 'both',
            source: '',
            startDate: '',
            endDate: '',
            search: ''
        };
        this.loadFeed(false);
    }

    showLoading() {
        this.loadingEl.style.display = 'flex';
    }

    hideLoading() {
        this.loadingEl.style.display = 'none';
    }

    showEmpty() {
        this.emptyEl.style.display = 'flex';
    }

    hideEmpty() {
        this.emptyEl.style.display = 'none';
    }

    formatDate(dateStr) {
        const date = new Date(dateStr);
        const now = new Date();
        const diff = now - date;
        const seconds = Math.floor(diff / 1000);
        const minutes = Math.floor(seconds / 60);
        const hours = Math.floor(minutes / 60);
        const days = Math.floor(hours / 24);

        if (days > 7) {
            return date.toLocaleDateString('en-US', {
                month: 'short',
                day: 'numeric',
                year: date.getFullYear() !== now.getFullYear() ? 'numeric' : undefined
            });
        } else if (days > 0) {
            return `${days}d ago`;
        } else if (hours > 0) {
            return `${hours}h ago`;
        } else if (minutes > 0) {
            return `${minutes}m ago`;
        } else {
            return 'Just now';
        }
    }

    getInitials(name) {
        if (name.startsWith('@')) {
            return name.substring(1, 3).toUpperCase();
        }
        return name.substring(0, 2).toUpperCase();
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    showNotification(message, type = 'info') {
        // Trigger notification via app
        if (window.app) {
            window.app.showNotification(message, type);
        }
    }
}

// Initialize feed manager when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.feedManager = new FeedManager();
});
