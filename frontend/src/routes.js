// src/routes.js
import Home from './components/Home.svelte';
import Login from './components/Login.svelte';
import Register from './components/Register.svelte';
import Profile from './components/Profile.svelte';
import CreatePost from './components/CreatePost.svelte';
import EditPost from './components/EditPost.svelte';
import BlogPost from './components/BlogPost.svelte';
import AuthGuard from './components/AuthGuard.svelte';
import { ROUTES } from './config';

// Define routes with optional guards and props
export const routes = [
  {
    path: ROUTES.HOME,
    component: Home
  },
  {
    path: ROUTES.LOGIN,
    component: Login
  },
  {
    path: ROUTES.REGISTER,
    component: Register
  },
  {
    path: `${ROUTES.VIEW_POST}/:id`,
    component: BlogPost
  },
  {
    path: ROUTES.PROFILE,
    component: AuthGuard,
    props: {
      childComponent: Profile
    }
  },
  {
    path: ROUTES.CREATE_POST,
    component: AuthGuard,
    props: {
      childComponent: CreatePost
    }
  },
  {
    path: `${ROUTES.EDIT_POST}/:id`,
    component: AuthGuard,
    props: (route) => ({
      childComponent: EditPost,
      id: route.params.id
    })
  }
];