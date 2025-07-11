from odoo import models, fields, api
from datetime import datetime, timedelta


class SocialMediaFilter(models.Model):
    _name = 'social_media.filter'
    _description = 'Social Media Filter'
    _order = 'sequence, name'
    
    name = fields.Char(string='Filter Name', required=True)
    user_id = fields.Many2one(
        'res.users',
        string='User',
        required=True,
        default=lambda self: self.env.user,
        ondelete='cascade'
    )
    filter_type = fields.Selection([
        ('keyword', 'Keyword'),
        ('author', 'Author'),
        ('hashtag', 'Hashtag'),
        ('date_range', 'Date Range'),
        ('engagement', 'Minimum Engagement'),
        ('media_type', 'Media Type'),
    ], string='Filter Type', required=True)
    filter_value = fields.Text(
        string='Filter Value',
        required=True,
        help='Value depends on filter type:\n'
             '- Keyword: Text to search for\n'
             '- Author: Username (without @)\n'
             '- Hashtag: Hashtag (without #)\n'
             '- Date Range: Format "days:7" for last 7 days\n'
             '- Engagement: Minimum number (e.g., "100")\n'
             '- Media Type: "image", "video", "gif"'
    )
    filter_mode = fields.Selection([
        ('include', 'Include'),
        ('exclude', 'Exclude'),
    ], string='Mode', default='include', required=True)
    sequence = fields.Integer(string='Sequence', default=10)
    active = fields.Boolean(string='Active', default=True)
    description = fields.Text(string='Description')
    
    # Statistics
    last_applied = fields.Datetime(string='Last Applied', readonly=True)
    match_count = fields.Integer(string='Matches Found', readonly=True)
    
    @api.constrains('filter_type', 'filter_value')
    def _check_filter_value(self):
        for filter_rec in self:
            if filter_rec.filter_type == 'date_range':
                # Validate date range format
                if ':' not in filter_rec.filter_value:
                    raise ValueError(
                        'Date range must be in format "days:N" where N is number of days'
                    )
                try:
                    parts = filter_rec.filter_value.split(':')
                    if parts[0] != 'days':
                        raise ValueError('Date range must start with "days:"')
                    int(parts[1])
                except (ValueError, IndexError):
                    raise ValueError(
                        'Invalid date range format. Use "days:7" for last 7 days'
                    )
            elif filter_rec.filter_type == 'engagement':
                try:
                    int(filter_rec.filter_value)
                except ValueError:
                    raise ValueError('Engagement value must be a number')
    
    def apply_to_posts(self, posts):
        """Apply this filter to a recordset of posts"""
        self.ensure_one()
        
        if self.filter_type == 'keyword':
            filtered = posts.filtered(
                lambda p: self.filter_value.lower() in (p.content or '').lower()
            )
        elif self.filter_type == 'author':
            filtered = posts.filtered(
                lambda p: p.author_username == self.filter_value
            )
        elif self.filter_type == 'hashtag':
            hashtag = self.filter_value.lstrip('#')
            filtered = posts.filtered(
                lambda p: f'#{hashtag}' in (p.content or '')
            )
        elif self.filter_type == 'date_range':
            days = int(self.filter_value.split(':')[1])
            date_limit = fields.Datetime.now() - timedelta(days=days)
            filtered = posts.filtered(
                lambda p: p.posted_at >= date_limit
            )
        elif self.filter_type == 'engagement':
            min_engagement = int(self.filter_value)
            filtered = posts.filtered(
                lambda p: self._get_post_engagement(p) >= min_engagement
            )
        elif self.filter_type == 'media_type':
            filtered = posts.filtered(
                lambda p: self._post_has_media_type(p, self.filter_value)
            )
        else:
            filtered = posts
        
        # Update statistics
        self.write({
            'last_applied': fields.Datetime.now(),
            'match_count': len(filtered)
        })
        
        # Apply mode (include/exclude)
        if self.filter_mode == 'include':
            return filtered
        else:
            return posts - filtered
    
    def _get_post_engagement(self, post):
        """Calculate total engagement for a post"""
        total = 0
        if post.post_metadata:
            if post.service == 'twitter':
                metrics = post.post_metadata.get('public_metrics', {})
                total = (
                    metrics.get('like_count', 0) +
                    metrics.get('retweet_count', 0) +
                    metrics.get('reply_count', 0)
                )
            elif post.service == 'facebook':
                total = (
                    post.post_metadata.get('likes', {}).get('summary', {}).get('total_count', 0) +
                    post.post_metadata.get('comments', {}).get('summary', {}).get('total_count', 0) +
                    post.post_metadata.get('shares', {}).get('count', 0)
                )
        return total
    
    def _post_has_media_type(self, post, media_type):
        """Check if post contains specified media type"""
        if not post.post_metadata:
            return False
        
        if post.service == 'twitter':
            media = post.post_metadata.get('attachments', {}).get('media', [])
            for item in media:
                if item.get('type') == media_type:
                    return True
        elif post.service == 'facebook':
            attachments = post.post_metadata.get('attachments', {}).get('data', [])
            for attachment in attachments:
                if attachment.get('type') == media_type:
                    return True
        
        return False
    
    @api.model
    def get_user_filters(self, user_id=None):
        """Get all active filters for a user"""
        if not user_id:
            user_id = self.env.user.id
        
        return self.search([
            ('user_id', '=', user_id),
            ('active', '=', True)
        ])
    
    def action_test_filter(self):
        """Test this filter on recent posts"""
        self.ensure_one()
        
        # Get recent posts for the user
        posts = self.env['social_media.post'].search([
            ('user_id', '=', self.user_id.id)
        ], limit=100)
        
        filtered_posts = self.apply_to_posts(posts)
        
        return {
            'name': f'Filter Test Results: {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'social_media.post',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', filtered_posts.ids)],
            'context': {
                'search_default_group_by_service': 1,
            }
        }