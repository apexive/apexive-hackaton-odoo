from odoo import models, fields, api
from odoo.exceptions import UserError
from datetime import datetime, timedelta
import json
import logging

_logger = logging.getLogger(__name__)


class SocialMediaAccount(models.Model):
    _name = 'social_media.account'
    _description = 'Social Media Account'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'display_name'
    
    provider_id = fields.Many2one(
        'social_media.provider',
        string='Provider',
        required=True,
        ondelete='cascade'
    )
    user_id = fields.Many2one(
        'res.users',
        string='User',
        required=True,
        default=lambda self: self.env.user,
        ondelete='cascade'
    )
    account_name = fields.Char(
        string='Account Name',
        help='Display name for this account'
    )
    account_username = fields.Char(
        string='Username',
        help='Username or handle on the platform'
    )
    external_account_id = fields.Char(
        string='External Account ID',
        help='User ID on the social media platform'
    )
    access_token = fields.Char(
        string='Access Token',
        groups='social_media.group_social_media_manager'
    )
    refresh_token = fields.Char(
        string='Refresh Token',
        groups='social_media.group_social_media_manager'
    )
    token_expiry = fields.Datetime(string='Token Expiry')
    account_metadata = fields.Json(
        string='Account Metadata',
        help='Additional account information (profile pic, stats, etc.)'
    )
    last_sync = fields.Datetime(string='Last Sync')
    active = fields.Boolean(string='Active', default=True)
    
    # Related fields
    service = fields.Selection(
        related='provider_id.service',
        string='Service',
        store=True,
        readonly=True
    )
    company_id = fields.Many2one(
        related='provider_id.company_id',
        string='Company',
        store=True,
        readonly=True
    )
    
    # Relations
    profile_ids = fields.One2many(
        'social_media.profile',
        'account_id',
        string='Profiles'
    )
    post_ids = fields.One2many(
        'social_media.post',
        'account_id',
        string='Posts'
    )
    
    display_name = fields.Char(
        string='Display Name',
        compute='_compute_display_name',
        store=True
    )
    
    is_token_expired = fields.Boolean(
        string='Token Expired',
        compute='_compute_is_token_expired'
    )
    
    @api.depends('account_name', 'account_username', 'provider_id.name')
    def _compute_display_name(self):
        for account in self:
            name_parts = []
            if account.account_name:
                name_parts.append(account.account_name)
            if account.account_username:
                name_parts.append(f"@{account.account_username}")
            if not name_parts and account.provider_id:
                name_parts.append(account.provider_id.name)
            account.display_name = ' - '.join(name_parts) or 'Social Media Account'
    
    @api.depends('token_expiry')
    def _compute_is_token_expired(self):
        for account in self:
            if not account.token_expiry:
                account.is_token_expired = False
            else:
                account.is_token_expired = fields.Datetime.now() > account.token_expiry
    
    def action_refresh_token(self):
        """Refresh the access token using refresh token"""
        self.ensure_one()
        if not self.refresh_token:
            raise UserError("No refresh token available for this account.")
        
        try:
            token_data = self.provider_id.refresh_access_token(self)
            self.write({
                'access_token': token_data.get('access_token'),
                'refresh_token': token_data.get('refresh_token', self.refresh_token),
                'token_expiry': datetime.now() + timedelta(
                    seconds=token_data.get('expires_in', 3600)
                )
            })
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Success',
                    'message': 'Token refreshed successfully',
                    'type': 'success',
                }
            }
        except Exception as e:
            _logger.error(f"Token refresh failed: {str(e)}")
            raise UserError(f"Failed to refresh token: {str(e)}")
    
    def action_sync_following(self):
        """Sync the list of accounts this user follows"""
        self.ensure_one()
        if self.is_token_expired:
            self.action_refresh_token()
        
        try:
            following_data = self.provider_id.fetch_following(self)
            self._process_following_data(following_data)
            self.last_sync = fields.Datetime.now()
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Success',
                    'message': f'Synced {len(following_data)} following profiles',
                    'type': 'success',
                }
            }
        except Exception as e:
            _logger.error(f"Following sync failed: {str(e)}")
            raise UserError(f"Failed to sync following: {str(e)}")
    
    def action_fetch_posts(self):
        """Fetch recent posts from followed accounts"""
        self.ensure_one()
        if self.is_token_expired:
            self.action_refresh_token()
        
        # Get active filters for this user
        filters = self.env['social_media.filter'].search([
            ('user_id', '=', self.user_id.id),
            ('active', '=', True)
        ])
        
        filter_dict = {}
        for f in filters:
            if f.filter_type not in filter_dict:
                filter_dict[f.filter_type] = []
            filter_dict[f.filter_type].append(f.filter_value)
        
        try:
            posts_data = self.provider_id.fetch_posts(self, filters=filter_dict)
            self._process_posts_data(posts_data)
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Success',
                    'message': f'Fetched {len(posts_data)} new posts',
                    'type': 'success',
                }
            }
        except Exception as e:
            _logger.error(f"Posts fetch failed: {str(e)}")
            raise UserError(f"Failed to fetch posts: {str(e)}")
    
    def _process_following_data(self, following_data):
        """Process and store following profiles data"""
        Profile = self.env['social_media.profile']
        
        for profile_info in following_data:
            existing = Profile.search([
                ('account_id', '=', self.id),
                ('external_profile_id', '=', profile_info['id'])
            ])
            
            profile_vals = {
                'account_id': self.id,
                'external_profile_id': profile_info['id'],
                'username': profile_info.get('username', ''),
                'display_name': profile_info.get('name', ''),
                'profile_type': 'following',
                'profile_metadata': profile_info.get('metadata', {}),
                'last_fetched': fields.Datetime.now(),
            }
            
            if existing:
                existing.write(profile_vals)
            else:
                Profile.create(profile_vals)
    
    def _process_posts_data(self, posts_data):
        """Process and store posts data"""
        Post = self.env['social_media.post']
        Profile = self.env['social_media.profile']
        
        for post_info in posts_data:
            # Find the profile
            profile = Profile.search([
                ('account_id', '=', self.id),
                ('external_profile_id', '=', post_info.get('author_id'))
            ], limit=1)
            
            if not profile:
                continue
            
            # Check if post already exists
            existing = Post.search([
                ('account_id', '=', self.id),
                ('external_post_id', '=', post_info['id'])
            ])
            
            if not existing:
                Post.create({
                    'account_id': self.id,
                    'profile_id': profile.id,
                    'external_post_id': post_info['id'],
                    'content': post_info.get('text', ''),
                    'post_metadata': post_info.get('metadata', {}),
                    'posted_at': post_info.get('created_at'),
                    'fetched_at': fields.Datetime.now(),
                })
    
    @api.model
    def cron_refresh_expired_tokens(self):
        """Cron job to refresh expired tokens"""
        expired_accounts = self.search([
            ('token_expiry', '<=', fields.Datetime.now()),
            ('refresh_token', '!=', False),
            ('active', '=', True)
        ])
        
        for account in expired_accounts:
            try:
                account.action_refresh_token()
            except Exception as e:
                _logger.error(
                    f"Failed to refresh token for account {account.display_name}: {str(e)}"
                )
    
    @api.model
    def cron_sync_posts(self):
        """Cron job to sync posts from all active accounts"""
        active_accounts = self.search([
            ('active', '=', True),
            ('access_token', '!=', False)
        ])
        
        for account in active_accounts:
            try:
                account.action_fetch_posts()
            except Exception as e:
                _logger.error(
                    f"Failed to sync posts for account {account.display_name}: {str(e)}"
                )
    
    def action_view_profiles(self):
        """View profiles for this account"""
        self.ensure_one()
        return {
            'name': f'Profiles - {self.display_name}',
            'type': 'ir.actions.act_window',
            'res_model': 'social_media.profile',
            'view_mode': 'tree,form',
            'domain': [('account_id', '=', self.id)],
            'context': {'default_account_id': self.id}
        }
    
    def action_view_posts(self):
        """View posts for this account"""
        self.ensure_one()
        return {
            'name': f'Posts - {self.display_name}',
            'type': 'ir.actions.act_window',
            'res_model': 'social_media.post',
            'view_mode': 'tree,form',
            'domain': [('account_id', '=', self.id)],
            'context': {'default_account_id': self.id}
        }