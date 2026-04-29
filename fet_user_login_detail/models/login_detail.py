# -*- coding: utf-8 -*-
###############################################################################
import logging
import os
import glob
import hashlib
from odoo import fields, models, api, _
from odoo.exceptions import UserError, AccessError
from odoo.tools import config
from odoo.http import request
from datetime import datetime, timedelta
import time
import json

_logger = logging.getLogger(__name__)

class LoginDetail(models.Model):
    _name = 'login.detail'
    _description = 'Login Detail'
    _order = 'create_date desc'
    _rec_name = 'login'

    user_id = fields.Many2one('res.users', string='User', required=True, ondelete='cascade')
    login = fields.Char(string='Login Name')
    ip_address = fields.Char(string='IP Address', size=50)
    user_agent = fields.Char(string='User Agent')
    session_id = fields.Char(string='Session ID (Filesystem)', size=128)  # SHA-1 hash

    status = fields.Selection([
        ('success', 'Success'),
        ('failed', 'Failed'),
    ], string='Status', default='success')
    message = fields.Text(string='Error Message')
    login_date = fields.Datetime(string='Login Date', required=True, default=fields.Datetime.now)
    device = fields.Char("Device")
    os = fields.Char("Operating System")
    browser = fields.Char("Browser")
    session_expiry = fields.Datetime(string="Session Expiry", compute="_compute_session_info", store=False)
    is_session_active = fields.Boolean(string="Session Active", compute="_compute_session_info", store=False)
    active = fields.Boolean(string="Active", default=True)



    def _get_session_directory(self):
        """Get the session directory path"""
        possible_paths = [
            os.path.join(config['data_dir'], 'sessions'),
            os.path.expanduser('~/.local/share/Odoo/sessions'),
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                return path
        return None

    def _find_session_file(self, session_id):
        """Find session file by its normalized session ID"""
        if not session_id or session_id in ['N/A', 'PENDING']:
            return None
            
        session_dir = self._get_session_directory()
        if not session_dir:
            return None
        
        if len(session_id) >= 2:
            subdir = session_id[:2]
            session_file = os.path.join(session_dir, subdir, session_id)
            if os.path.exists(session_file):
                return session_file
        
        return None

    def _compute_session_info(self):
        now = time.time()

        for record in self:
            record.is_session_active = False
            record.active = False

            if not record.session_id:
                continue

            session_file = record._find_session_file(record.session_id)
            if not session_file:
                continue

            try:
                stat = os.stat(session_file)
                last_activity = stat.st_mtime
                if now - last_activity < 7200:  # 5 minutes
                    record.is_session_active = True
                    record.active = True
            except:
                pass


    def action_kill_session(self):
        self.ensure_one()

        if not self.env.user.has_group('base.group_system'):
            raise AccessError("Only administrators can kill sessions!")

        record = self.exists()
        if not record:
            return
        if not record.session_id:
            raise UserError("No valid session ID")

        session_file = record._find_session_file(record.session_id)
        try:
            # 1. delete session file FIRST (this forces logout)
            if session_file and os.path.exists(session_file):
                os.remove(session_file)

            # 2. DO NOT unlink immediately → only mark
            record.sudo().write({
                'status': 'failed',
                'message': f'Session killed by {self.env.user.login}',
                'is_session_active': False,
                'active': False,
            })

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Session Killed',
                    'message': f'Session terminated for {record.login}',
                    'type': 'success',
                }
            }
        except Exception as e:
            raise UserError(f"Failed to kill session: {str(e)}")

    def action_view_session_details(self):
        """View detailed session information"""
        self.ensure_one()
        
        if not self.session_id or self.session_id in ['N/A', 'PENDING']:
            raise UserError(f"No valid session ID for user {self.login}")
        
        info = []
        info.append("=" * 60)
        info.append(f"SESSION DETAILS FOR: {self.login}")
        info.append("=" * 60)
        info.append(f"Session ID (normalized): {self.session_id}")
        info.append(f"Raw Session ID: {self.session_id or 'N/A'}")
        info.append(f"Login Date: {self.login_date}")
        info.append(f"IP Address: {self.ip_address}")
        info.append(f"Device: {self.device}")
        info.append(f"OS: {self.os}")
        info.append(f"Browser: {self.browser}")
        
        # Check session file
        session_file = self._find_session_file(self.session_id)
        if session_file:
            try:
                file_stat = os.stat(session_file)
                info.append("\n" + "-" * 40)
                info.append("SESSION FILE INFORMATION:")
                info.append(f"  Path: {session_file}")
                info.append(f"  Size: {file_stat.st_size} bytes")
                info.append(f"  Created: {fields.Datetime.fromtimestamp(file_stat.st_ctime)}")
                info.append(f"  Modified: {datetime.fromtimestamp(file_stat.st_mtime)}")
                
                # Calculate age
                age = datetime.now() - datetime.fromtimestamp(file_stat.st_mtime)
                info.append(f"  Age: {age.days} days, {age.seconds//3600} hours")
            except Exception as e:
                info.append(f"\n❌ Error reading session file: {e}")
        else:
            info.append("\n" + "-" * 40)
            info.append("SESSION FILE NOT FOUND")
            info.append(f"Expected location: {self._get_session_directory()}/{self.session_id[:2]}/{self.session_id}")
        
        info.append("=" * 60)
        
        raise UserError("\n".join(info))


    def action_verify_session(self):
        """Verify if the session file exists and show debug info"""
        self.ensure_one()
        
        if not self.session_id or self.session_id == 'N/A':
            raise UserError("No session ID stored for this record")
        
        session_dir = '/opt/odoo17/.local/share/Odoo/sessions'
        expected_path = f"{session_dir}/{self.session_id[:2]}/{self.session_id}"
        
        info = []
        info.append("=" * 60)
        info.append(f"SESSION VERIFICATION FOR: {self.login}")
        info.append("=" * 60)
        info.append(f"Stored Session ID: {self.session_id}")
        info.append(f"Raw Session ID: {self.session_id or 'N/A'}")
        info.append(f"Expected path: {expected_path}")
        info.append(f"File exists: {os.path.exists(expected_path)}")
        
        if os.path.exists(expected_path):
            try:
                file_stat = os.stat(expected_path)
                info.append(f"File size: {file_stat.st_size} bytes")
                info.append(f"Last modified: {datetime.fromtimestamp(file_stat.st_mtime)}")
            except Exception as e:
                info.append(f"Error reading file: {e}")
        
        # Also check if we can find the session by raw ID
        raw_normalized = hashlib.sha1(self.session_id.encode('utf-8')).hexdigest() if self.session_id else 'N/A'
        info.append(f"\nRaw ID normalized: {raw_normalized}")
        info.append(f"Matches stored: {raw_normalized == self.session_id}")
        
        # List all session files for this user (by searching content)
        info.append("\nSearching for sessions belonging to this user...")
        session_dir_path = session_dir
        found_sessions = []
        
        if os.path.exists(session_dir_path):
            for subdir in os.listdir(session_dir_path):
                subdir_path = os.path.join(session_dir_path, subdir)
                if os.path.isdir(subdir_path):
                    for filename in os.listdir(subdir_path):
                        filepath = os.path.join(subdir_path, filename)
                        try:
                            with open(filepath, 'r', errors='ignore') as f:
                                content = f.read()
                                if f'"uid": {self.user_id.id}' in content:
                                    found_sessions.append(filename)
                        except:
                            pass
        
        if found_sessions:
            info.append(f"Found sessions: {', '.join(found_sessions)}")
        else:
            info.append("No sessions found for this user")
        
        info.append("=" * 60)
        
        raise UserError("\n".join(info))






            
