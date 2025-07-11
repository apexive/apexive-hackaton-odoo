from odoo import models, fields, api
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class SocialMediaProvider(models.Model):
    _name = 'social_media.provider'
    _description = 'Social Media Provider'
    _order = 'sequence, name'
    
    name = fields.Char(string='Provider Name', required=True)
    service = fields.Selection(
        selection='_get_available_services',
        string='Service',
        required=True,
        help='Social media platform type'
    )
    api_version = fields.Char(string='API Version', default='v2')
    oauth_authorize_url = fields.Char(string='OAuth Authorization URL')
    oauth_token_url = fields.Char(string='OAuth Token URL')
    api_base_url = fields.Char(string='API Base URL')
    scopes = fields.Text(
        string='OAuth Scopes',
        help='Comma-separated list of OAuth scopes required'
    )
    client_id = fields.Char(string='Client ID')
    client_secret = fields.Char(string='Client Secret')
    sequence = fields.Integer(string='Sequence', default=10)
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company
    )
    active = fields.Boolean(string='Active', default=True)
    account_ids = fields.One2many(
        'social_media.account',
        'provider_id',
        string='Connected Accounts'
    )
    
    @api.model
    def _get_available_services(self):
        """Get list of available social media services"""
        return [
            ('twitter', 'Twitter'),
            ('facebook', 'Facebook'),
        ]
    
    def _dispatch(self, method, *args, record=None, **kwargs):
        """Dispatch method calls to service-specific implementations"""
        record = record or self
        service_method = f"{record.service}_{method}"
        if hasattr(record, service_method):
            return getattr(record, service_method)(*args, **kwargs)
        else:
            raise UserError(
                f"Method '{method}' not implemented for service '{record.service}'"
            )
    
    def authenticate(self, redirect_uri):
        """Generate OAuth authentication URL"""
        return self._dispatch('authenticate', redirect_uri=redirect_uri)
    
    def exchange_code_for_token(self, code, redirect_uri):
        """Exchange authorization code for access token"""
        return self._dispatch(
            'exchange_code_for_token',
            code=code,
            redirect_uri=redirect_uri
        )
    
    def refresh_access_token(self, account):
        """Refresh expired access token"""
        return self._dispatch('refresh_access_token', account=account)
    
    def fetch_user_profile(self, account):
        """Fetch authenticated user's profile information"""
        return self._dispatch('fetch_user_profile', account=account)
    
    def fetch_following(self, account, cursor=None, limit=100):
        """Fetch list of accounts the user follows"""
        return self._dispatch(
            'fetch_following',
            account=account,
            cursor=cursor,
            limit=limit
        )
    
    def fetch_posts(self, account, filters=None, cursor=None, limit=50):
        """Fetch posts from followed accounts with optional filters"""
        return self._dispatch(
            'fetch_posts',
            account=account,
            filters=filters or {},
            cursor=cursor,
            limit=limit
        )
    
    def get_oauth_url(self, redirect_uri, state=None):
        """Build OAuth authorization URL with parameters"""
        params = {
            'client_id': self.client_id,
            'redirect_uri': redirect_uri,
            'response_type': 'code',
            'scope': self.scopes,
        }
        if state:
            params['state'] = state
        
        return self._dispatch('build_oauth_url', params=params)
    
    @api.model
    def create_default_providers(self):
        """Create default provider configurations"""
        providers_data = [
            {
                'name': 'Twitter API v2',
                'service': 'twitter',
                'api_version': 'v2',
                'oauth_authorize_url': 'https://twitter.com/i/oauth2/authorize',
                'oauth_token_url': 'https://api.twitter.com/2/oauth2/token',
                'api_base_url': 'https://api.twitter.com/2',
                'scopes': 'tweet.read,users.read,follows.read,offline.access',
            },
            {
                'name': 'Facebook Graph API',
                'service': 'facebook',
                'api_version': 'v18.0',
                'oauth_authorize_url': 'https://www.facebook.com/v18.0/dialog/oauth',
                'oauth_token_url': 'https://graph.facebook.com/v18.0/oauth/access_token',
                'api_base_url': 'https://graph.facebook.com/v18.0',
                'scopes': 'public_profile,email,user_posts,user_friends',
            },
        ]
        
        for data in providers_data:
            if not self.search([('service', '=', data['service'])]):
                self.create(data)
    
    def action_view_accounts(self):
        """View connected accounts for this provider"""
        self.ensure_one()
        return {
            'name': f'Accounts - {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'social_media.account',
            'view_mode': 'tree,form',
            'domain': [('provider_id', '=', self.id)],
            'context': {'default_provider_id': self.id}
        }