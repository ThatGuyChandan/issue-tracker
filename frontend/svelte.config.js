import adapter from '@sveltejs/adapter-auto';

export default {
  kit: {
    adapter: adapter(),
    alias: {
      $components: 'src/components',
      $lib: 'src/lib',
    },
  },
}; 