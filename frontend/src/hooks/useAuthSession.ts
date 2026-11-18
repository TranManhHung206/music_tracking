import { useState, useCallback, useEffect, useRef } from 'react';
import type { UserProfile } from '../types/auth';
import { api } from '../services/api';
import type { ToastMessage } from '../components/ui/Toast';

interface UseAuthSessionOptions {
  addToast: (type: ToastMessage['type'], message: string) => void;
  onDemoModeExit?: () => void;
}

/** Quản lý phiên đăng nhập Spotify OAuth (exchange_code một lần) và kiểm tra session không chặn luồng sync. */
export function useAuthSession({ addToast, onDemoModeExit }: UseAuthSessionOptions) {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [isCheckingAuth, setIsCheckingAuth] = useState(true);
  const [authCheckError, setAuthCheckError] = useState<string | null>(null);
  const [isLoggingIn, setIsLoggingIn] = useState(false);
  const hasInitializedRef = useRef(false);

  const checkSession = useCallback(async () => {
    setIsCheckingAuth(true);
    setAuthCheckError(null);
    try {
      const currentUser = await api.getCurrentUser();
      if (currentUser) {
        setUser(currentUser);
        onDemoModeExit?.();
      } else {
        setUser(null);
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Lỗi kết nối máy chủ xác thực.';
      setAuthCheckError(msg);
    } finally {
      setIsCheckingAuth(false);
    }
  }, [onDemoModeExit]);

  useEffect(() => {
    if (hasInitializedRef.current) return;
    hasInitializedRef.current = true;

    const params = new URLSearchParams(window.location.search);
    const exchangeCode = params.get('exchange_code');
    const authSuccess = params.get('auth_success');
    const authError = params.get('auth_error');

    if (authError) {
      window.history.replaceState({}, document.title, window.location.pathname);
      setTimeout(() => {
        addToast('error', decodeURIComponent(authError));
      }, 0);
    }

    if (exchangeCode) {
      window.history.replaceState({}, document.title, window.location.pathname);
      api
        .exchangeSpotifyCode(exchangeCode)
        .then((res) => {
          localStorage.setItem('access_token', res.token);
          setUser(res.user);
          onDemoModeExit?.();
          setAuthCheckError(null);
          addToast('success', 'Đăng nhập Spotify thành công! Đang tải hồ sơ của bạn...');
        })
        .catch((err) => {
          const msg = err instanceof Error ? err.message : 'Trao đổi phiên đăng nhập thất bại.';
          addToast('error', msg);
        })
        .finally(() => {
          setIsCheckingAuth(false);
        });
      return;
    }

    if (authSuccess) {
      window.history.replaceState({}, document.title, window.location.pathname);
    }

    api
      .getCurrentUser()
      .then((currentUser) => {
        if (currentUser) {
          setUser(currentUser);
          onDemoModeExit?.();
          if (authSuccess) {
            addToast('success', 'Đăng nhập Spotify thành công! Đang tải hồ sơ của bạn...');
          }
        }
      })
      .catch((err) => {
        const msg = err instanceof Error ? err.message : 'Không thể xác minh phiên làm việc.';
        setAuthCheckError(msg);
      })
      .finally(() => {
        setIsCheckingAuth(false);
      });
  }, [addToast, onDemoModeExit]);

  const handleLogin = useCallback(async () => {
    setIsLoggingIn(true);
    try {
      const authUrl = await api.getLoginUrl();
      if (authUrl && authUrl !== '#') {
        window.location.href = authUrl;
      } else {
        addToast('error', 'Không thể khởi tạo đường dẫn đăng nhập Spotify. Vui lòng kiểm tra Backend.');
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Lỗi kết nối máy chủ xác thực.';
      addToast('error', msg);
    } finally {
      setIsLoggingIn(false);
    }
  }, [addToast]);

  const handleLogout = useCallback(async () => {
    try {
      await api.logout();
    } finally {
      setUser(null);
      onDemoModeExit?.();
      addToast('info', 'Bạn đã đăng xuất thành công.');
    }
  }, [addToast, onDemoModeExit]);

  return {
    user,
    setUser,
    isCheckingAuth,
    authCheckError,
    isLoggingIn,
    checkSession,
    handleLogin,
    handleLogout,
  };
}
