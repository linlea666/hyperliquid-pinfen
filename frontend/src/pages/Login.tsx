import { FormEvent, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiPostPublic } from '../api/client';

export default function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    try {
      const res = await apiPostPublic<{ access_token: string }>('/auth/login', { email, password });
      localStorage.setItem('authToken', res.access_token);
      navigate('/dashboard');
    } catch (err: any) {
      setError(err.message || '登录失败');
    }
  };

  return (
    <div className="login-page">
      <form className="login-card" onSubmit={handleSubmit}>
        <h2>后台登录</h2>
        <label>
          邮箱
          <input value={email} onChange={(e) => setEmail(e.target.value)} placeholder="admin@example.com" />
        </label>
        <label>
          密码
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="请输入密码" />
        </label>
        {error && <p className="error">{error}</p>}
        <button className="btn primary" type="submit">
          登录
        </button>
      </form>
    </div>
  );
}
