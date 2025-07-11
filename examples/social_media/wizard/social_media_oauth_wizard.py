from odoo import models, fields, api
from odoo.exceptions import UserError
import secrets
import logging

_logger = logging.getLogger(__name__)


class SocialMediaOAuthWizard(models.TransientModel):
    _name = 'social_media.oauth.wizard'
    _description = 'Social Media OAuth Authorization Wizard'
    
    provider_id = fields.Many2one(
        'social_media.provider',
        string='Provider',
        required=True,
        domain=[('active', '=', True)]
    )
    account_name = fields.Char(
        string='Account Name',
        help='Display name for this account'
    )
    
    # OAuth flow fields
    state = fields.Char(string='OAuth State', readonly=True)
    code_verifier = fields.Char(string='Code Verifier', readonly=True)
    auth_url = fields.Char(string='Authorization URL', readonly=True)
    
    # Step tracking
    step = fields.Selection([
        ('start', 'Start'),
        ('authorize', 'Authorize'),
        ('complete', 'Complete')
    ], default='start', string='Step')
    
    @api.model
    def default_get(self, fields_list):
        """Set default provider if called from provider form"""
        res = super().default_get(fields_list)
        
        if self.env.context.get('default_provider_id'):
            res['provider_id'] = self.env.context['default_provider_id']
        
        return res
    
    def action_start_oauth(self):
        """Start OAuth flow by generating authorization URL"""
        self.ensure_one()
        
        if not self.provider_id.client_id:
            raise UserError(
                "Provider is not configured. Please set the Client ID and Client Secret."
            )
        
        # Generate redirect URI
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        redirect_uri = f"{base_url}/social_media/oauth/callback"
        
        # Get authorization URL from provider
        auth_data = self.provider_id.authenticate(redirect_uri)
        
        # Update wizard with OAuth data
        self.write({
            'auth_url': auth_data['auth_url'],
            'state': auth_data.get('state'),
            'code_verifier': auth_data.get('code_verifier'),
            'step': 'authorize'
        })
        
        return {
            'name': 'Authorize Social Media Account',
            'type': 'ir.actions.act_window',
            'res_model': 'social_media.oauth.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }
    
    def action_open_authorization_url(self):
        """Open authorization URL in new tab"""
        self.ensure_one()
        
        if not self.auth_url:
            raise UserError("Authorization URL not generated. Please start OAuth flow first.")
        
        return {
            'type': 'ir.actions.act_url',
            'url': self.auth_url,
            'target': 'new',
        }
    
    def action_complete_oauth(self, code=None):
        """Complete OAuth flow after user authorization"""
        self.ensure_one()
        
        if not code:
            raise UserError("Authorization code is required to complete OAuth flow.")
        
        # Generate redirect URI (same as in start)
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        redirect_uri = f"{base_url}/social_media/oauth/callback"
        
        try:
            # Exchange code for token
            if self.provider_id.service == 'twitter':
                token_data = self.provider_id.twitter_exchange_code_for_token(
                    code, redirect_uri, self.code_verifier
                )
            else:
                token_data = self.provider_id.exchange_code_for_token(code, redirect_uri)
            
            # Create account record
            account_vals = {
                'provider_id': self.provider_id.id,
                'account_name': self.account_name or f"{self.provider_id.name} Account",
                'access_token': token_data.get('access_token'),
                'refresh_token': token_data.get('refresh_token'),
            }
            
            # Set token expiry if provided
            if token_data.get('expires_in'):
                from datetime import datetime, timedelta
                account_vals['token_expiry'] = datetime.now() + timedelta(
                    seconds=token_data['expires_in']
                )
            
            # Create account
            account = self.env['social_media.account'].create(account_vals)
            
            # Fetch user profile to populate account details
            try:
                profile_data = self.provider_id.fetch_user_profile(account)
                account.write({
                    'account_username': profile_data.get('username'),
                    'external_account_id': profile_data.get('id'),
                    'account_metadata': profile_data.get('metadata', {}),
                })
            except Exception as e:
                _logger.warning(f"Failed to fetch profile data: {str(e)}")
            
            self.step = 'complete'
            
            return {
                'name': 'Account Connected Successfully',
                'type': 'ir.actions.act_window',
                'res_model': 'social_media.account',
                'res_id': account.id,
                'view_mode': 'form',
                'target': 'current',
            }
            
        except Exception as e:
            _logger.error(f"OAuth completion failed: {str(e)}")
            raise UserError(f"Failed to complete OAuth: {str(e)}")
    
    def action_cancel(self):
        """Cancel OAuth flow"""
        return {'type': 'ir.actions.act_window_close'}
    
    @api.model
    def handle_oauth_callback(self, provider_id, code, state):
        """Handle OAuth callback from external service"""
        # Find the wizard record by state
        wizard = self.search([
            ('provider_id', '=', provider_id),
            ('state', '=', state)
        ], limit=1)
        
        if not wizard:
            raise UserError("Invalid OAuth state. Please restart the authorization process.")
        
        # Complete OAuth flow
        return wizard.action_complete_oauth(code)
    
    def action_test_connection(self):
        """Test connection with current provider settings"""
        self.ensure_one()
        
        if not self.provider_id.client_id:
            raise UserError("Provider Client ID is not configured.")
        
        try:
            # Try to generate auth URL to test basic configuration
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            redirect_uri = f"{base_url}/social_media/oauth/callback"
            
            auth_data = self.provider_id.authenticate(redirect_uri)
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Connection Test',
                    'message': 'Provider configuration is valid. You can proceed with account connection.',
                    'type': 'success',
                }
            }
        except Exception as e:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Connection Test Failed',
                    'message': f'Provider configuration error: {str(e)}',
                    'type': 'danger',
                }
            }