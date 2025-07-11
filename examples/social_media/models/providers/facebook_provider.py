from odoo import models, fields, api
from odoo.exceptions import UserError
import requests
import secrets
import logging
from urllib.parse import urlencode

_logger = logging.getLogger(__name__)


class FacebookProvider(models.Model):
    _inherit = 'social_media.provider'
    
    @api.model
    def _get_available_services(self):
        services = super()._get_available_services()
        return services
    
    def facebook_authenticate(self, redirect_uri):
        """Generate Facebook OAuth authentication URL"""
        self.ensure_one()
        
        params = {
            'client_id': self.client_id,
            'redirect_uri': redirect_uri,
            'response_type': 'code',
            'scope': self.scopes,
            'state': secrets.token_urlsafe(16),
        }
        
        auth_url = f"{self.oauth_authorize_url}?{urlencode(params)}"
        
        return {
            'auth_url': auth_url,
            'state': params['state'],
        }
    
    def facebook_build_oauth_url(self, params):
        """Build OAuth URL with parameters"""
        return f"{self.oauth_authorize_url}?{urlencode(params)}"
    
    def facebook_exchange_code_for_token(self, code, redirect_uri):
        """Exchange authorization code for access token"""
        self.ensure_one()
        
        params = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'redirect_uri': redirect_uri,
            'code': code,
        }
        
        try:
            response = requests.get(
                self.oauth_token_url,
                params=params
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            _logger.error(f"Facebook token exchange failed: {str(e)}")
            raise UserError(f"Failed to exchange code for token: {str(e)}")
    
    def facebook_refresh_access_token(self, account):
        """Refresh Facebook access token"""
        self.ensure_one()
        
        # Facebook uses long-lived tokens that don't need frequent refresh
        # If refresh is needed, exchange current token for a new long-lived one
        params = {
            'grant_type': 'fb_exchange_token',
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'fb_exchange_token': account.access_token,
        }
        
        try:
            response = requests.get(
                self.oauth_token_url,
                params=params
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            _logger.error(f"Facebook token refresh failed: {str(e)}")
            raise UserError(f"Failed to refresh token: {str(e)}")
    
    def facebook_fetch_user_profile(self, account):
        """Fetch authenticated user's Facebook profile"""
        self.ensure_one()
        
        params = {
            'access_token': account.access_token,
            'fields': 'id,name,email,picture',
        }
        
        try:
            response = requests.get(
                f"{self.api_base_url}/me",
                params=params
            )
            response.raise_for_status()
            data = response.json()
            
            return {
                'id': data['id'],
                'username': data.get('email', '').split('@')[0],
                'name': data['name'],
                'metadata': {
                    'email': data.get('email'),
                    'picture': data.get('picture', {}).get('data', {}).get('url'),
                }
            }
        except requests.exceptions.RequestException as e:
            _logger.error(f"Facebook profile fetch failed: {str(e)}")
            raise UserError(f"Failed to fetch profile: {str(e)}")
    
    def facebook_fetch_following(self, account, cursor=None, limit=100):
        """Fetch list of Facebook friends/pages the user follows"""
        self.ensure_one()
        
        # Note: Facebook's friend list access is restricted
        # This method focuses on pages the user follows
        
        params = {
            'access_token': account.access_token,
            'limit': min(limit, 500),
            'fields': 'id,name,picture,category,about',
        }
        
        if cursor:
            params['after'] = cursor
        
        try:
            response = requests.get(
                f"{self.api_base_url}/me/likes",
                params=params
            )
            response.raise_for_status()
            data = response.json()
            
            following = []
            for page in data.get('data', []):
                following.append({
                    'id': page['id'],
                    'username': page.get('name', '').replace(' ', '').lower(),
                    'name': page['name'],
                    'metadata': {
                        'picture': page.get('picture', {}).get('data', {}).get('url'),
                        'category': page.get('category'),
                        'about': page.get('about'),
                    }
                })
            
            return following
        except requests.exceptions.RequestException as e:
            _logger.error(f"Facebook following fetch failed: {str(e)}")
            raise UserError(f"Failed to fetch following: {str(e)}")
    
    def facebook_fetch_posts(self, account, filters=None, cursor=None, limit=50):
        """Fetch recent posts from Facebook feed"""
        self.ensure_one()
        
        params = {
            'access_token': account.access_token,
            'limit': min(limit, 100),
            'fields': 'id,message,created_time,from,likes.summary(true),comments.summary(true),shares,attachments,permalink_url',
        }
        
        if cursor:
            params['after'] = cursor
        
        try:
            # Get posts from user's feed
            response = requests.get(
                f"{self.api_base_url}/me/feed",
                params=params
            )
            response.raise_for_status()
            data = response.json()
            
            posts = []
            for post in data.get('data', []):
                # Skip posts without message (like shared links without text)
                if not post.get('message'):
                    continue
                
                # Apply filters if provided
                if filters and not self._facebook_post_matches_filters(post, filters):
                    continue
                
                posts.append({
                    'id': post['id'],
                    'text': post.get('message', ''),
                    'created_at': post.get('created_time'),
                    'author_id': post.get('from', {}).get('id'),
                    'author_username': post.get('from', {}).get('name', '').replace(' ', '').lower(),
                    'author_name': post.get('from', {}).get('name'),
                    'metadata': {
                        'likes': post.get('likes', {}),
                        'comments': post.get('comments', {}),
                        'shares': post.get('shares', {}),
                        'attachments': post.get('attachments', {}),
                        'permalink_url': post.get('permalink_url'),
                    }
                })
            
            return posts
        except requests.exceptions.RequestException as e:
            _logger.error(f"Facebook posts fetch failed: {str(e)}")
            raise UserError(f"Failed to fetch posts: {str(e)}")
    
    def _facebook_post_matches_filters(self, post, filters):
        """Check if a Facebook post matches the provided filters"""
        message = post.get('message', '').lower()
        
        # Keyword filter
        if 'keyword' in filters:
            if not any(keyword.lower() in message for keyword in filters['keyword']):
                return False
        
        # Exclude keyword filter
        if 'exclude_keyword' in filters:
            if any(keyword.lower() in message for keyword in filters['exclude_keyword']):
                return False
        
        # Author filter
        if 'author' in filters:
            author_name = post.get('from', {}).get('name', '').lower()
            if not any(author.lower() in author_name for author in filters['author']):
                return False
        
        # Engagement filter (minimum likes)
        if 'engagement' in filters:
            min_engagement = int(filters['engagement'][0])
            likes_count = post.get('likes', {}).get('summary', {}).get('total_count', 0)
            comments_count = post.get('comments', {}).get('summary', {}).get('total_count', 0)
            shares_count = post.get('shares', {}).get('count', 0)
            
            total_engagement = likes_count + comments_count + shares_count
            if total_engagement < min_engagement:
                return False
        
        return True