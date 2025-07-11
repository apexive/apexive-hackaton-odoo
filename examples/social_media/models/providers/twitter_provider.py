from odoo import models, fields, api
from odoo.exceptions import UserError
import requests
import base64
import hashlib
import secrets
from urllib.parse import urlencode, quote
import logging

_logger = logging.getLogger(__name__)


class TwitterProvider(models.Model):
    _inherit = 'social_media.provider'
    
    @api.model
    def _get_available_services(self):
        services = super()._get_available_services()
        return services
    
    def twitter_authenticate(self, redirect_uri):
        """Generate Twitter OAuth 2.0 authentication URL"""
        self.ensure_one()
        
        # Generate PKCE parameters
        code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8').rstrip('=')
        code_challenge = base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode()).digest()
        ).decode('utf-8').rstrip('=')
        
        # Store code_verifier in session or temporary storage
        # For now, we'll return it to be stored by the wizard
        
        params = {
            'response_type': 'code',
            'client_id': self.client_id,
            'redirect_uri': redirect_uri,
            'scope': self.scopes,
            'state': secrets.token_urlsafe(16),
            'code_challenge': code_challenge,
            'code_challenge_method': 'S256',
        }
        
        auth_url = f"{self.oauth_authorize_url}?{urlencode(params)}"
        
        return {
            'auth_url': auth_url,
            'code_verifier': code_verifier,
            'state': params['state'],
        }
    
    def twitter_build_oauth_url(self, params):
        """Build OAuth URL with parameters"""
        return f"{self.oauth_authorize_url}?{urlencode(params)}"
    
    def twitter_exchange_code_for_token(self, code, redirect_uri, code_verifier=None):
        """Exchange authorization code for access token"""
        self.ensure_one()
        
        data = {
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': redirect_uri,
            'client_id': self.client_id,
        }
        
        if code_verifier:
            data['code_verifier'] = code_verifier
        
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
        }
        
        if self.client_secret:
            # Use client credentials
            auth = base64.b64encode(f"{self.client_id}:{self.client_secret}".encode()).decode()
            headers['Authorization'] = f'Basic {auth}'
        
        try:
            response = requests.post(
                self.oauth_token_url,
                data=data,
                headers=headers
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            _logger.error(f"Twitter token exchange failed: {str(e)}")
            raise UserError(f"Failed to exchange code for token: {str(e)}")
    
    def twitter_refresh_access_token(self, account):
        """Refresh Twitter access token"""
        self.ensure_one()
        
        data = {
            'grant_type': 'refresh_token',
            'refresh_token': account.refresh_token,
            'client_id': self.client_id,
        }
        
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
        }
        
        if self.client_secret:
            auth = base64.b64encode(f"{self.client_id}:{self.client_secret}".encode()).decode()
            headers['Authorization'] = f'Basic {auth}'
        
        try:
            response = requests.post(
                self.oauth_token_url,
                data=data,
                headers=headers
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            _logger.error(f"Twitter token refresh failed: {str(e)}")
            raise UserError(f"Failed to refresh token: {str(e)}")
    
    def twitter_fetch_user_profile(self, account):
        """Fetch authenticated user's Twitter profile"""
        self.ensure_one()
        
        headers = {
            'Authorization': f'Bearer {account.access_token}',
        }
        
        try:
            response = requests.get(
                f"{self.api_base_url}/users/me",
                headers=headers,
                params={
                    'user.fields': 'id,name,username,profile_image_url,public_metrics,description'
                }
            )
            response.raise_for_status()
            data = response.json()
            
            return {
                'id': data['data']['id'],
                'username': data['data']['username'],
                'name': data['data']['name'],
                'metadata': {
                    'profile_image_url': data['data'].get('profile_image_url'),
                    'description': data['data'].get('description'),
                    'public_metrics': data['data'].get('public_metrics', {}),
                }
            }
        except requests.exceptions.RequestException as e:
            _logger.error(f"Twitter profile fetch failed: {str(e)}")
            raise UserError(f"Failed to fetch profile: {str(e)}")
    
    def twitter_fetch_following(self, account, cursor=None, limit=100):
        """Fetch list of accounts the user follows on Twitter"""
        self.ensure_one()
        
        headers = {
            'Authorization': f'Bearer {account.access_token}',
        }
        
        params = {
            'max_results': min(limit, 1000),
            'user.fields': 'id,name,username,profile_image_url,description,public_metrics',
        }
        
        if cursor:
            params['pagination_token'] = cursor
        
        try:
            response = requests.get(
                f"{self.api_base_url}/users/{account.external_account_id}/following",
                headers=headers,
                params=params
            )
            response.raise_for_status()
            data = response.json()
            
            following = []
            for user in data.get('data', []):
                following.append({
                    'id': user['id'],
                    'username': user['username'],
                    'name': user['name'],
                    'metadata': {
                        'profile_image_url': user.get('profile_image_url'),
                        'description': user.get('description'),
                        'public_metrics': user.get('public_metrics', {}),
                    }
                })
            
            return following
        except requests.exceptions.RequestException as e:
            _logger.error(f"Twitter following fetch failed: {str(e)}")
            raise UserError(f"Failed to fetch following: {str(e)}")
    
    def twitter_fetch_posts(self, account, filters=None, cursor=None, limit=50):
        """Fetch recent tweets from followed accounts"""
        self.ensure_one()
        
        headers = {
            'Authorization': f'Bearer {account.access_token}',
        }
        
        # Build search query based on filters
        query_parts = []
        
        # Get tweets from people user follows
        query_parts.append('from:following')
        
        # Apply filters
        if filters:
            if 'keyword' in filters:
                keywords = ' OR '.join([f'"{kw}"' for kw in filters['keyword']])
                query_parts.append(f'({keywords})')
            
            if 'hashtag' in filters:
                hashtags = ' OR '.join([f'#{tag.lstrip("#")}' for tag in filters['hashtag']])
                query_parts.append(f'({hashtags})')
            
            if 'author' in filters:
                authors = ' OR '.join([f'from:{author}' for author in filters['author']])
                query_parts.append(f'({authors})')
            
            if 'exclude_keyword' in filters:
                for kw in filters['exclude_keyword']:
                    query_parts.append(f'-"{kw}"')
        
        # Exclude retweets and replies by default
        query_parts.append('-is:retweet')
        query_parts.append('-is:reply')
        
        query = ' '.join(query_parts)
        
        params = {
            'query': query,
            'max_results': min(limit, 100),
            'tweet.fields': 'id,text,created_at,author_id,public_metrics,attachments,entities',
            'expansions': 'author_id,attachments.media_keys',
            'user.fields': 'id,name,username',
            'media.fields': 'url,type,preview_image_url',
        }
        
        if cursor:
            params['next_token'] = cursor
        
        try:
            response = requests.get(
                f"{self.api_base_url}/tweets/search/recent",
                headers=headers,
                params=params
            )
            response.raise_for_status()
            data = response.json()
            
            # Process tweets
            posts = []
            users_map = {}
            media_map = {}
            
            # Build user and media maps
            for user in data.get('includes', {}).get('users', []):
                users_map[user['id']] = user
            
            for media in data.get('includes', {}).get('media', []):
                media_map[media['media_key']] = media
            
            for tweet in data.get('data', []):
                author = users_map.get(tweet['author_id'], {})
                
                # Add media URLs to metadata
                media_urls = []
                if tweet.get('attachments', {}).get('media_keys'):
                    for media_key in tweet['attachments']['media_keys']:
                        if media_key in media_map:
                            media_urls.append(media_map[media_key].get('url') or 
                                            media_map[media_key].get('preview_image_url'))
                
                posts.append({
                    'id': tweet['id'],
                    'text': tweet['text'],
                    'created_at': tweet['created_at'],
                    'author_id': tweet['author_id'],
                    'author_username': author.get('username'),
                    'author_name': author.get('name'),
                    'metadata': {
                        'public_metrics': tweet.get('public_metrics', {}),
                        'attachments': tweet.get('attachments', {}),
                        'entities': tweet.get('entities', {}),
                        'media_urls': media_urls,
                    }
                })
            
            return posts
        except requests.exceptions.RequestException as e:
            _logger.error(f"Twitter posts fetch failed: {str(e)}")
            raise UserError(f"Failed to fetch posts: {str(e)}")