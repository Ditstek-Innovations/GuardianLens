// CS-AU-12 — the behaviours a refactor loses first: the toggle flips the
// input type without touching the value, the icon never leaks text into the
// accessible tree, and paste is never blocked (CS-AU-15).
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';

import { FormField } from './FormField';
import { PasswordInput } from './PasswordInput';

// Rendered inside FormField because that is the only way the primitive is
// used: FormField clones its child with id/aria props, and PasswordInput must
// forward them to the real <input>.
const renderField = (error?: string) =>
  render(
    <FormField label="Password" required {...(error !== undefined ? { error } : {})}>
      <PasswordInput name="password" autoComplete="new-password" />
    </FormField>,
  );

const getInput = (): HTMLInputElement =>
  screen.getByLabelText(/password/i, { selector: 'input' });

describe('PasswordInput', () => {
  it('toggles input type and aria-pressed, with an accessible name for each state', async () => {
    const user = userEvent.setup();
    renderField();

    expect(getInput()).toHaveAttribute('type', 'password');
    const toggle = screen.getByRole('button', { name: 'Show password' });
    expect(toggle).toHaveAttribute('aria-pressed', 'false');
    expect(toggle).toHaveAttribute('type', 'button'); // never submits the form

    await user.click(toggle);
    expect(getInput()).toHaveAttribute('type', 'text');
    expect(screen.getByRole('button', { name: 'Hide password' })).toHaveAttribute(
      'aria-pressed',
      'true',
    );

    await user.click(screen.getByRole('button', { name: 'Hide password' }));
    expect(getInput()).toHaveAttribute('type', 'password');
    expect(screen.getByRole('button', { name: 'Show password' })).toHaveAttribute(
      'aria-pressed',
      'false',
    );
  });

  it('renders the toggle as an aria-hidden inline SVG with no text leak', () => {
    renderField();
    const toggle = screen.getByRole('button', { name: 'Show password' });

    expect(toggle.textContent).toBe('');
    const svg = toggle.querySelector('svg');
    expect(svg).not.toBeNull();
    expect(svg).toHaveAttribute('aria-hidden', 'true');
  });

  it('never clears the value on toggle', async () => {
    const user = userEvent.setup();
    renderField();

    await user.type(getInput(), 'correct horse battery');
    await user.click(screen.getByRole('button', { name: 'Show password' }));
    expect(getInput()).toHaveValue('correct horse battery');
    await user.click(screen.getByRole('button', { name: 'Hide password' }));
    expect(getInput()).toHaveValue('correct horse battery');
    expect(getInput()).toHaveAttribute('type', 'password');
  });

  it('never blocks paste (CS-AU-15)', async () => {
    const user = userEvent.setup();
    renderField();

    await user.click(getInput());
    await user.paste('pasted-passphrase-42');
    expect(getInput()).toHaveValue('pasted-passphrase-42');
  });

  it('forwards FormField-injected aria wiring to the real input (CS-FM-03)', () => {
    renderField('Password must be at least 12 characters.');
    const input = getInput();

    expect(input).toHaveAttribute('aria-invalid', 'true');
    const describedBy = input.getAttribute('aria-describedby');
    expect(describedBy).not.toBeNull();
    expect(document.getElementById(describedBy ?? '')).toHaveTextContent(
      'Password must be at least 12 characters.',
    );
  });
});
