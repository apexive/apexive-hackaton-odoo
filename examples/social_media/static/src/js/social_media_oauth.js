odoo.define('social_media.oauth', function (require) {
    'use strict';
    
    var core = require('web.core');
    var Dialog = require('web.Dialog');
    var Widget = require('web.Widget');
    
    var _t = core._t;
    
    var SocialMediaOAuth = Widget.extend({
        
        /**
         * Open OAuth authorization in popup window
         */
        openOAuthPopup: function(authUrl, callback) {
            var popup = window.open(
                authUrl,
                'social_media_oauth',
                'width=600,height=700,scrollbars=yes,resizable=yes'
            );
            
            // Check if popup was blocked
            if (!popup || popup.closed || typeof popup.closed === 'undefined') {
                Dialog.alert(this, _t('Popup blocked. Please allow popups for this site and try again.'));
                return;
            }
            
            // Monitor popup
            var checkClosed = setInterval(function() {
                if (popup.closed) {
                    clearInterval(checkClosed);
                    if (callback) {
                        callback();
                    }
                }
            }, 1000);
            
            return popup;
        },
        
        /**
         * Handle OAuth completion
         */
        handleOAuthComplete: function(data) {
            if (data.success) {
                this.displayNotification({
                    title: _t('Success'),
                    message: _t('Account connected successfully!'),
                    type: 'success'
                });
                
                // Reload the view to show new account
                if (this.getParent() && this.getParent().reload) {
                    this.getParent().reload();
                }
            } else {
                this.displayNotification({
                    title: _t('Error'),
                    message: data.message || _t('Failed to connect account'),
                    type: 'danger'
                });
            }
        },
        
        /**
         * Test OAuth configuration
         */
        testOAuthConfig: function(providerId) {
            var self = this;
            
            this._rpc({
                route: '/social_media/oauth/test',
                params: {
                    provider_id: providerId
                }
            }).then(function(result) {
                if (result.indexOf('successful') !== -1) {
                    self.displayNotification({
                        title: _t('Test Successful'),
                        message: _t('OAuth configuration is valid'),
                        type: 'success'
                    });
                } else {
                    self.displayNotification({
                        title: _t('Test Failed'),
                        message: result,
                        type: 'danger'
                    });
                }
            }).catch(function(error) {
                self.displayNotification({
                    title: _t('Test Error'),
                    message: error.message || _t('Failed to test configuration'),
                    type: 'danger'
                });
            });
        }
    });
    
    return SocialMediaOAuth;
});