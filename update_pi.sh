#!/bin/bash

# Quick update script for Pi deployment

echo "🔄 Updating ReolinkANPR on Pi..."

PI_IP="192.168.5.175"
PI_USER="pi"  # Change if different
PROJECT_DIR="~/ReolinkANPR"

echo "📤 Pushing latest code to GitHub..."
git add -A
git commit -m "Update: cooldown + image notifications" || echo "No changes to commit"
git push

echo "📡 Connecting to Pi at $PI_IP..."

ssh $PI_USER@$PI_IP << 'ENDSSH'
cd ~/ReolinkANPR || exit 1

echo "⏸️  Stopping service..."
sudo systemctl stop reolink-anpr

echo "⬇️  Pulling latest code..."
git pull origin main

echo "📦 Updating dependencies..."
source venv/bin/activate
pip install -r requirements.txt

echo "▶️  Starting service..."
sudo systemctl start reolink-anpr

echo "✅ Update complete!"
echo ""
echo "📋 Checking service status..."
sudo systemctl status reolink-anpr --no-pager -l | head -20

echo ""
echo "📝 Recent logs:"
tail -20 logs/anpr.log
ENDSSH

echo ""
echo "✅ Pi updated! Check above for any errors."
echo "🔍 To monitor logs: ssh $PI_USER@$PI_IP 'tail -f ~/ReolinkANPR/logs/anpr.log'"

