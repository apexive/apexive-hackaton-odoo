# Social Media Integration Module

A comprehensive Odoo 16.0 module for connecting and managing multiple social media accounts, fetching posts from followed accounts, and applying custom filters.

## Features

### 🔌 Multi-Platform Support
- **Twitter/X Integration** with OAuth 2.0 + PKCE
- **Facebook Integration** with Graph API
- Extensible architecture for adding new platforms

### 👥 Multi-Account Management
- Connect multiple accounts per platform
- User-specific account management
- Automatic token refresh
- Account status monitoring

### 📊 Content Fetching
- Fetch posts from followed accounts
- Configurable sync intervals
- Automatic filtering during fetch
- Rich metadata storage

### 🔍 Advanced Filtering
- **Keyword filters** - Include/exclude posts with specific text
- **Author filters** - Filter by specific usernames
- **Hashtag filters** - Filter by hashtags
- **Date range filters** - Posts from specific time periods
- **Engagement filters** - Minimum likes/comments/shares
- **Media type filters** - Images, videos, GIFs

### 🔐 Security & Access Control
- User-specific data isolation
- Role-based access (User/Manager)
- Secure credential storage
- Company-wide provider configuration

## Installation

1. Copy the `social_media` folder to your Odoo addons directory
2. Update the addons list: `odoo-bin -u social_media`
3. Install the module from Apps menu

## Setup

### 1. Configure Providers

**For Twitter:**
1. Go to Social Media → Configuration → Providers
2. Open "Twitter API v2" provider
3. Set your Twitter App credentials:
   - Client ID
   - Client Secret (optional for public clients)
4. Save the configuration

**For Facebook:**
1. Go to Social Media → Configuration → Providers  
2. Open "Facebook Graph API" provider
3. Set your Facebook App credentials:
   - App ID (Client ID)
   - App Secret (Client Secret)
4. Save the configuration

### 2. Connect Accounts

1. Go to Social Media → My Accounts
2. Click "Connect New Account"
3. Select a provider and enter account name
4. Click "Start OAuth"
5. Authorize the app in the popup window
6. Account will be connected automatically

### 3. Configure Filters (Optional)

1. Go to Social Media → Filters
2. Create filters to customize fetched content:
   - **Include mode**: Only show posts matching the filter
   - **Exclude mode**: Hide posts matching the filter

### 4. Sync Content

**Manual Sync:**
- From account form: Click "Sync Following" or "Fetch Posts"
- From account list: Use action buttons

**Automatic Sync:**
- Enable cron jobs in Technical → Automation → Scheduled Actions
- "Social Media: Sync Posts" - Fetches new posts (disabled by default)
- "Social Media: Sync Following Lists" - Updates following lists (disabled by default)

## Usage

### Viewing Content

**Posts Dashboard:**
- Social Media → Posts
- View all fetched posts across accounts
- Filter by platform, author, date
- Open original posts in browser

**Following Management:**
- Social Media → Configuration → Profiles
- View all profiles you follow
- See post counts per profile

### Managing Filters

**Filter Types:**
- **Keyword**: `"machine learning"` or `"AI"`
- **Author**: `"elonmusk"` (without @)
- **Hashtag**: `"python"` (without #)
- **Date Range**: `"days:7"` (last 7 days)
- **Engagement**: `"100"` (minimum total engagement)
- **Media Type**: `"image"`, `"video"`, or `"gif"`

**Filter Modes:**
- **Include**: Show only matching posts
- **Exclude**: Hide matching posts

## API Integration

### Twitter API Setup

1. Create a Twitter Developer account
2. Create a new App with OAuth 2.0 enabled
3. Set redirect URI: `https://yourdomain.com/social_media/oauth/callback`
4. Note the Client ID and Client Secret

### Facebook API Setup

1. Create a Facebook Developer account
2. Create a new App
3. Add Facebook Login product
4. Set redirect URI: `https://yourdomain.com/social_media/oauth/callback`
5. Note the App ID and App Secret

## Architecture

### Models

```
social_media.provider     # Platform configurations (Twitter, Facebook)
social_media.account      # User-specific accounts with OAuth tokens
social_media.profile      # Followed profiles/users
social_media.post         # Fetched posts with metadata
social_media.filter       # User-defined content filters
```

### Provider Pattern

The module uses a dispatch pattern similar to `llm_provider`:

```python
# Base provider with dispatch
def fetch_posts(self, account, filters=None):
    return self._dispatch('fetch_posts', account=account, filters=filters)

# Service-specific implementation
def twitter_fetch_posts(self, account, filters=None):
    # Twitter-specific API calls
```

### Security

- **User Isolation**: Users only see their own accounts and data
- **Manager Role**: Can configure providers and view all accounts
- **Credential Security**: OAuth tokens stored securely
- **Company Separation**: Multi-company support

## Customization

### Adding New Platforms

1. Create a new provider file in `models/providers/`
2. Implement service-specific methods:
   - `{service}_authenticate()`
   - `{service}_fetch_posts()`
   - `{service}_fetch_following()`
3. Add service to `_get_available_services()`

### Extending Filters

1. Add new filter types to `social_media.filter`
2. Implement filter logic in `apply_to_posts()`
3. Update help text in views

### Custom Post Processing

Override `_process_posts_data()` in `social_media.account` to add custom post processing logic.

## Troubleshooting

### Common Issues

**OAuth Popup Blocked:**
- Enable popups for your Odoo domain
- Check browser popup settings

**Token Expired:**
- Tokens refresh automatically via cron
- Manually refresh from account form

**API Rate Limits:**
- Twitter: 300 requests per 15 minutes
- Facebook: Varies by endpoint
- Adjust sync frequency accordingly

**Missing Posts:**
- Check account filters
- Verify OAuth scopes
- Review API response in logs

### Debug Mode

Enable debug logging for detailed API responses:
```python
import logging
logging.getLogger('social_media').setLevel(logging.DEBUG)
```

## Support

For issues and feature requests, please contact the development team or create an issue in the project repository.

## License

This module is licensed under LGPL-3.0.