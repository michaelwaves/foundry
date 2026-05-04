insert into storage.buckets (id, name, public)
values ('inputs', 'inputs', false), ('outputs', 'outputs', false)
on conflict (id) do nothing;

create policy "users read own inputs" on storage.objects
  for select using (bucket_id = 'inputs' and auth.uid()::text = (storage.foldername(name))[1]);

create policy "users write own inputs" on storage.objects
  for insert with check (bucket_id = 'inputs' and auth.uid()::text = (storage.foldername(name))[1]);

create policy "users read own outputs" on storage.objects
  for select using (bucket_id = 'outputs' and auth.uid()::text = (storage.foldername(name))[1]);
