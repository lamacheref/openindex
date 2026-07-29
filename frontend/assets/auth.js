// Auth désactivée - stub inoffensif pour compatibilité ascendante
const pb = {
  authStore: {
    isValid: true,
    model: { name: 'Administrateur', email: 'admin@openindex.local', role: 'admin', isAdmin: true, is_admin: true },
    onChange: () => {},
    clear: () => {},
  },
};

function onPbReady(callback) { callback(pb); }

function checkAuth() { return true; }

function isTruthyAdminValue(value) { return value === true || value === 1 || (typeof value === 'string' && ['true', '1', 'yes'].includes(value.trim().toLowerCase())); }

function resolveAdminStatus(user) { return user ? (isTruthyAdminValue(user.isAdmin) || isTruthyAdminValue(user.is_admin) || isTruthyAdminValue(user.admin) || user.role === 'admin') : false; }

function isAdmin() { return true; }

function enforceAuth() { return true; }
function enforceAdminOnly() { return true; }
function enforceUserAuth() { return true; }
function hideAdminElements() {}
function showAdminElements() {}
function protectBlock(blockId, adminOnly) {}

async function login(email, password) { return { success: true, user: pb.authStore.model }; }
function logout() {}
function redirectIfNotAuthenticated() {}
function redirectIfNotAdmin() {}
function initAuth() {}
function onAuthChange(callback) { callback(true, pb.authStore.model); }
