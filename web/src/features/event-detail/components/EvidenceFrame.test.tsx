import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { EvidenceFrame } from './EvidenceFrame';

describe('EvidenceFrame', () => {
  it('reports onLoaded only when the image element has actually loaded', () => {
    const onLoaded = vi.fn();
    render(
      <EvidenceFrame
        url="blob:mock"
        isPending={false}
        isError={false}
        alt="Evidence frame — Bay 3 entrance"
        onLoaded={onLoaded}
        onFailed={() => undefined}
      />,
    );

    expect(onLoaded).not.toHaveBeenCalled();
    fireEvent.load(screen.getByAltText(/bay 3 entrance/i));
    expect(onLoaded).toHaveBeenCalledTimes(1);
  });

  it('shows the explicit evidence-unavailable state on failure — never a silent broken image (F-6)', () => {
    render(
      <EvidenceFrame
        url={null}
        isPending={false}
        isError
        alt="Evidence frame"
        onLoaded={() => undefined}
        onFailed={() => undefined}
      />,
    );

    expect(screen.getByRole('alert')).toHaveTextContent(/evidence unavailable — storage failure/i);
  });
});
