from odoo import http
from odoo.http import request
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class SocialMediaOAuthController(http.Controller):
    
    @http.route('/social_media/oauth/callback', type='http', auth='user', methods=['GET'])
    def oauth_callback(self, **kwargs):
        """Handle OAuth callback from social media platforms"""
        
        code = kwargs.get('code')
        state = kwargs.get('state')
        error = kwargs.get('error')
        
        if error:
            error_description = kwargs.get('error_description', 'Unknown error')
            _logger.error(f"OAuth error: {error} - {error_description}")
            return request.render('social_media.oauth_error', {
                'error': error,
                'error_description': error_description
            })
        
        if not code or not state:
            _logger.error("OAuth callback missing required parameters")
            return request.render('social_media.oauth_error', {
                'error': 'invalid_request',
                'error_description': 'Missing authorization code or state parameter'
            })
        
        try:
            # Find the wizard record by state
            wizard = request.env['social_media.oauth.wizard'].search([
                ('state', '=', state)
            ], limit=1)
            
            if not wizard:
                _logger.error(f"No wizard found for state: {state}")
                return request.render('social_media.oauth_error', {
                    'error': 'invalid_state',
                    'error_description': 'Invalid or expired OAuth state'
                })
            
            # Complete OAuth flow
            result = wizard.action_complete_oauth(code)
            
            # Return success page with JavaScript to close popup or redirect
            return request.render('social_media.oauth_success', {
                'account_name': wizard.account_name,
                'provider_name': wizard.provider_id.name,
                'redirect_url': '/web#menu_id=social_media.menu_social_media_accounts'
            })
            
        except UserError as e:
            _logger.error(f"OAuth completion failed: {str(e)}")
            return request.render('social_media.oauth_error', {
                'error': 'completion_failed',
                'error_description': str(e)
            })
        except Exception as e:
            _logger.error(f"Unexpected OAuth error: {str(e)}")
            return request.render('social_media.oauth_error', {
                'error': 'unexpected_error',
                'error_description': 'An unexpected error occurred during authorization'
            })
    
    @http.route('/social_media/oauth/test', type='http', auth='user', methods=['GET'])
    def test_oauth(self, **kwargs):
        """Test OAuth configuration"""
        provider_id = kwargs.get('provider_id')
        
        if not provider_id:
            return "Missing provider_id parameter"
        
        try:
            provider = request.env['social_media.provider'].browse(int(provider_id))
            if not provider.exists():
                return "Provider not found"
            
            # Test configuration
            base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
            redirect_uri = f"{base_url}/social_media/oauth/callback"
            
            auth_data = provider.authenticate(redirect_uri)
            
            return f"OAuth test successful. Auth URL: {auth_data['auth_url']}"
            
        except Exception as e:
            return f"OAuth test failed: {str(e)}"