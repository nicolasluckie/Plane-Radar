#!/usr/bin/env bash
# harden-pi.sh — Baseline hardening for Raspberry Pi running Debian 13 (Trixie)
# Mirrors ansible-homelab/playbooks/configure_vm.yml, adapted for Pi.
#
# Assumes:
#   - Admin user already exists (created during OS install)
#   - Script is run as root: sudo ./harden-pi.sh
#
# What it does:
#   - Full dist-upgrade + unattended-upgrades
#   - Installs essential packages
#   - Sets timezone and hostname
#   - Injects SSH public key for admin user, configures passwordless sudo
#   - Drops .bash_aliases onto admin user
#   - Hardens sshd_config (no root login, key-only auth)
#   - Configures UFW: deny in, allow out, allow SSH (22) + Plane-Radar web (8080)

set -euo pipefail

# ─── Colour helpers ───────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'
info()    { echo -e "${GREEN}[INFO]${NC}  $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
step()    { echo -e "\n${CYAN}──────────────────────────────────────${NC}"; echo -e "${CYAN}$*${NC}"; }
err()     { echo -e "${RED}[ERROR]${NC} $*" >&2; exit 1; }

# ─── Root check ───────────────────────────────────────────────────────────────
[[ $EUID -ne 0 ]] && err "Run as root: sudo ./harden-pi.sh"

# ─── Gather inputs ────────────────────────────────────────────────────────────
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "   Pi Hardening Script — Debian 13 (Trixie)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

read -rp "Admin username to configure [pi]: " ADMIN_USER
ADMIN_USER="${ADMIN_USER:-pi}"

# ─── Verify admin user exists ─────────────────────────────────────────────────
id "$ADMIN_USER" &>/dev/null || err "User '$ADMIN_USER' does not exist. Create it first."

read -rp "Hostname for this Pi [plane-radar-pi]: " NEW_HOSTNAME
NEW_HOSTNAME="${NEW_HOSTNAME:-plane-radar-pi}"

read -rp "Timezone [America/Toronto]: " TIMEZONE
TIMEZONE="${TIMEZONE:-America/Toronto}"

echo ""
echo "Paste your SSH public key (contents of ~/.ssh/id_ed25519.pub on your Mac):"
read -rp "> " SSH_PUBLIC_KEY
[[ -z "$SSH_PUBLIC_KEY" ]] && err "SSH public key cannot be empty."

echo ""
info "Summary:"
echo "  Admin user : $ADMIN_USER (existing)"
echo "  Hostname   : $NEW_HOSTNAME"
echo "  Timezone   : $TIMEZONE"
echo "  UFW ports  : 22/tcp (SSH), 8080/tcp (Plane-Radar web)"
echo ""
read -rp "Proceed? [y/N]: " CONFIRM
[[ "${CONFIRM,,}" != "y" ]] && { warn "Aborted."; exit 0; }

# ─── 1. System update ─────────────────────────────────────────────────────────
step "1/7  System update"
apt-get update -q
DEBIAN_FRONTEND=noninteractive apt-get dist-upgrade -y -q
apt-get autoremove -y -q
apt-get autoclean -q
info "System up to date."

# ─── 2. Unattended upgrades ───────────────────────────────────────────────────
step "2/7  Unattended upgrades"
DEBIAN_FRONTEND=noninteractive apt-get install -y -q unattended-upgrades
echo "unattended-upgrades unattended-upgrades/enable_auto_updates boolean true" \
  | debconf-set-selections
dpkg-reconfigure -f noninteractive unattended-upgrades
info "Unattended upgrades enabled."

# ─── 3. Essential packages ────────────────────────────────────────────────────
step "3/7  Essential packages"
DEBIAN_FRONTEND=noninteractive apt-get install -y -q \
  curl wget gnupg ca-certificates apt-transport-https \
  git htop ufw
info "Essential packages installed."

# ─── 4. Timezone + hostname ───────────────────────────────────────────────────
step "4/7  Timezone + hostname"
timedatectl set-timezone "$TIMEZONE"
info "Timezone set to $TIMEZONE."

hostnamectl set-hostname "$NEW_HOSTNAME"
# Update /etc/hosts — replace or insert 127.0.1.1 line
if grep -q '^127\.0\.1\.1' /etc/hosts; then
  sed -i "s/^127\.0\.1\.1.*/127.0.1.1 $NEW_HOSTNAME/" /etc/hosts
else
  echo "127.0.1.1 $NEW_HOSTNAME" >> /etc/hosts
fi
info "Hostname set to $NEW_HOSTNAME."

# ─── 5. User config (existing admin user) ─────────────────────────────────────────
step "5/7  User config"

# Ensure admin user is in sudo group
usermod -aG sudo "$ADMIN_USER"

# Passwordless sudo (mirrors Ansible lineinfile)
if grep -q '^%sudo' /etc/sudoers; then
  sed -i 's/^%sudo.*/%sudo ALL=(ALL:ALL) NOPASSWD: ALL/' /etc/sudoers
else
  echo '%sudo ALL=(ALL:ALL) NOPASSWD: ALL' >> /etc/sudoers
fi
visudo -cf /etc/sudoers || err "sudoers file is invalid — fix manually."
info "Passwordless sudo configured."

# SSH authorized key
SSH_DIR="/home/$ADMIN_USER/.ssh"
AUTH_KEYS="$SSH_DIR/authorized_keys"
mkdir -p "$SSH_DIR"
chmod 700 "$SSH_DIR"

# Avoid duplicate key entries
if ! grep -qF "$SSH_PUBLIC_KEY" "$AUTH_KEYS" 2>/dev/null; then
  echo "$SSH_PUBLIC_KEY" >> "$AUTH_KEYS"
  info "SSH public key added."
else
  warn "SSH public key already present — skipping."
fi

chmod 600 "$AUTH_KEYS"
chown -R "$ADMIN_USER:$ADMIN_USER" "$SSH_DIR"

# .bash_aliases (mirrors Ansible copy task)
cat > "/home/$ADMIN_USER/.bash_aliases" << 'EOF'
# System update aliases
alias update='sudo apt update -y && sudo apt upgrade -y'
alias update-clean='sudo apt autoclean -y && sudo apt autoremove -y'
alias full-update='sudo apt update && sudo apt upgrade -y && sudo apt clean -y && sudo apt autoclean -y'

# Plane-Radar service helpers
alias pr-status='sudo systemctl status plane-radar'
alias pr-logs='sudo journalctl -u plane-radar -f'
alias pr-restart='sudo systemctl restart plane-radar'

# Backup/restore functions
backup() { sudo tar -czpf "$(basename "$1")-bak-$(date +%Y-%m-%d).gz" "$1" && echo "Backup created: $(pwd)/$(basename "$1")-bak-$(date +%Y-%m-%d).gz" && echo "File size: $(du -h "$(basename "$1")-bak-$(date +%Y-%m-%d).gz" | cut -f1)"; }
restore() { sudo tar -xzf "$1" -C "$(pwd)" && echo "Backup restored to $(pwd)"; }
EOF

chown "$ADMIN_USER:$ADMIN_USER" "/home/$ADMIN_USER/.bash_aliases"
chmod 644 "/home/$ADMIN_USER/.bash_aliases"

# Source .bash_aliases from .bashrc if not already there
BASHRC="/home/$ADMIN_USER/.bashrc"
if ! grep -q 'bash_aliases' "$BASHRC" 2>/dev/null; then
  echo -e '\nif [ -f ~/.bash_aliases ]; then . ~/.bash_aliases; fi' >> "$BASHRC"
fi
info "Shell aliases configured."

# ─── 6. SSH hardening ─────────────────────────────────────────────────────────
step "6/7  SSH hardening"

SSHD_CONF="/etc/ssh/sshd_config"

# On Debian 13, drop-in overrides in /etc/ssh/sshd_config.d/ are cleaner
# and won't be clobbered by package updates.
DROPIN="/etc/ssh/sshd_config.d/99-harden.conf"
mkdir -p /etc/ssh/sshd_config.d

cat > "$DROPIN" << 'EOF'
# Applied by harden-pi.sh — mirrors ansible-homelab configure_vm.yml
PermitRootLogin no
PasswordAuthentication no
PubkeyAuthentication yes
X11Forwarding no
MaxAuthTries 3
EOF

chmod 600 "$DROPIN"

# Ensure sshd_config includes the drop-in directory (Debian 13 default: yes)
if ! grep -q 'Include /etc/ssh/sshd_config.d' "$SSHD_CONF" 2>/dev/null; then
  sed -i '1s|^|Include /etc/ssh/sshd_config.d/*.conf\n|' "$SSHD_CONF"
fi

# Validate config before restarting
sshd -t || err "sshd config test failed — check $DROPIN before restarting SSH."
systemctl restart ssh
info "SSH hardened and restarted."
warn "Password auth is now DISABLED. Ensure your SSH key works before closing this session."

# ─── 7. UFW firewall ──────────────────────────────────────────────────────────
step "7/7  UFW firewall"

ufw --force reset
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp    comment 'SSH'
ufw allow 8080/tcp  comment 'Plane-Radar web'
ufw --force enable
ufw status verbose
info "UFW configured and enabled."

# ─── Done ─────────────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}   Hardening complete!${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "  Next steps:"
echo "  1. Open a NEW terminal and verify SSH key login works before exiting this session"
echo "  2. Check UFW:     sudo ufw status verbose"
echo "  3. Check sshd:    sudo sshd -t && sudo systemctl status ssh"
echo ""
