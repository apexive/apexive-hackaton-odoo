from odoo import models, fields, api
from datetime import datetime


class SocialMediaPost(models.Model):
    _name = 'social_media.post'
    _description = 'Social Media Post'
    _order = 'posted_at desc'
    _inherit = ['mail.thread']
    
    account_id = fields.Many2one(
        'social_media.account',
        string='Account',
        required=True,
        ondelete='cascade'
    )
    profile_id = fields.Many2one(
        'social_media.profile',
        string='Author Profile',
        required=True,
        ondelete='cascade'
    )
    external_post_id = fields.Char(
        string='External Post ID',
        required=True
    )
    content = fields.Text(string='Content')
    post_metadata = fields.Json(
        string='Post Metadata',
        help='Additional post information (likes, shares, media URLs, etc.)'
    )
    posted_at = fields.Datetime(string='Posted At')
    fetched_at = fields.Datetime(
        string='Fetched At',
        default=fields.Datetime.now
    )
    
    # Related fields
    service = fields.Selection(
        related='account_id.service',
        string='Service',
        store=True,
        readonly=True
    )
    user_id = fields.Many2one(
        related='account_id.user_id',
        string='User',
        store=True,
        readonly=True
    )
    author_username = fields.Char(
        related='profile_id.username',
        string='Author Username',
        store=True,
        readonly=True
    )
    author_display_name = fields.Char(
        related='profile_id.display_name',
        string='Author Name',
        store=True,
        readonly=True
    )
    
    # Computed fields
    post_url = fields.Char(
        string='Post URL',
        compute='_compute_post_url'
    )
    media_urls = fields.Text(
        string='Media URLs',
        compute='_compute_media_info'
    )
    engagement_stats = fields.Char(
        string='Engagement',
        compute='_compute_engagement_stats'
    )
    
    _sql_constraints = [
        ('unique_post_per_account',
         'UNIQUE(account_id, external_post_id)',
         'Post ID must be unique per account!')
    ]
    
    @api.depends('service', 'external_post_id', 'post_metadata')
    def _compute_post_url(self):
        for post in self:
            if post.service == 'twitter':
                author_id = post.post_metadata.get('author_id', '')
                post.post_url = f"https://twitter.com/i/web/status/{post.external_post_id}"
            elif post.service == 'facebook':
                post_id = post.external_post_id
                if '_' in post_id:
                    post.post_url = f"https://www.facebook.com/{post_id.replace('_', '/posts/')}"
                else:
                    post.post_url = f"https://www.facebook.com/{post_id}"
            else:
                post.post_url = ''
    
    @api.depends('post_metadata')
    def _compute_media_info(self):
        for post in self:
            media_urls = []
            if post.post_metadata:
                # Extract media URLs based on service
                if post.service == 'twitter':
                    media = post.post_metadata.get('attachments', {}).get('media_keys', [])
                    media_urls = post.post_metadata.get('media_urls', [])
                elif post.service == 'facebook':
                    attachments = post.post_metadata.get('attachments', {})
                    if attachments.get('data'):
                        for attachment in attachments['data']:
                            if attachment.get('media'):
                                media_urls.append(attachment['media'].get('image', {}).get('src', ''))
            
            post.media_urls = '\n'.join(media_urls)
    
    @api.depends('post_metadata')
    def _compute_engagement_stats(self):
        for post in self:
            stats = []
            if post.post_metadata:
                # Extract engagement metrics based on service
                if post.service == 'twitter':
                    metrics = post.post_metadata.get('public_metrics', {})
                    if metrics.get('like_count'):
                        stats.append(f"❤️ {metrics['like_count']}")
                    if metrics.get('retweet_count'):
                        stats.append(f"🔁 {metrics['retweet_count']}")
                    if metrics.get('reply_count'):
                        stats.append(f"💬 {metrics['reply_count']}")
                elif post.service == 'facebook':
                    if post.post_metadata.get('likes'):
                        stats.append(f"👍 {post.post_metadata['likes'].get('summary', {}).get('total_count', 0)}")
                    if post.post_metadata.get('comments'):
                        stats.append(f"💬 {post.post_metadata['comments'].get('summary', {}).get('total_count', 0)}")
                    if post.post_metadata.get('shares'):
                        stats.append(f"↗️ {post.post_metadata['shares'].get('count', 0)}")
            
            post.engagement_stats = ' '.join(stats)
    
    def name_get(self):
        result = []
        for post in self:
            # Create a preview of the content
            content_preview = (post.content or '')[:50]
            if len(post.content or '') > 50:
                content_preview += '...'
            
            name = f"{post.author_username or post.author_display_name}: {content_preview}"
            result.append((post.id, name))
        return result
    
    def action_open_post_url(self):
        """Open the post in a new browser tab"""
        self.ensure_one()
        if self.post_url:
            return {
                'type': 'ir.actions.act_url',
                'url': self.post_url,
                'target': 'new',
            }
    
    @api.model
    def search_posts(self, query, filters=None):
        """Search posts with text and filters"""
        domain = []
        
        # Text search in content
        if query:
            domain.append(('content', 'ilike', query))
        
        # Apply filters
        if filters:
            if filters.get('authors'):
                domain.append(('author_username', 'in', filters['authors']))
            if filters.get('date_from'):
                domain.append(('posted_at', '>=', filters['date_from']))
            if filters.get('date_to'):
                domain.append(('posted_at', '<=', filters['date_to']))
            if filters.get('services'):
                domain.append(('service', 'in', filters['services']))
        
        return self.search(domain)