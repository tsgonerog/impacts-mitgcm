#include "COST_OPTIONS.h"

      subroutine cost_atlantic_heat( myThid )
C     /==========================================================\
C     | subroutine cost_atlantic_heat                            |
C     | o DINO_1deg: the meridional transport across one grid    |
C     |   row, from the surface over a set number of levels, as  |
C     |   a time mean over the end of the run: of volume, in Sv  |
C     |   (since 2026-10-29), or of heat, in PW (since           |
C     |   2026-10-31), as data.cost's cost_atl_quantity says.    |
C     |   The routine keeps the name pkg/cost calls it by        |
C     |   (cost_final.F). The tree file's form, kept here until  |
C     |   2026-10-29, is described at the end.                   |
C     \==========================================================/
       implicit none

C     == Global variables ===
#include "SIZE.h"
#include "EEPARAMS.h"
#include "PARAMS.h"
#include "GRID.h"
#include "cost.h"

C     ======== Routine arguments ======================
C     myThid - Thread number for this instance of the routine.
      integer myThid

#ifdef ALLOW_COST_ATLANTIC_HEAT
C     ========= Local variables =========================
      integer i, j, k, jg
      integer bi, bj
      _RL     tileTransport
      _RL     meanFrac
      LOGICAL doHeat

C     The cost J is
C
C       J = mult_atl * 1e-6 * < sum_i sum_{k<=kmax}
C                 vVel(i,jsec,k) dxG(i,jsec) drF(k) hFacS(i,jsec,k) >
C
C     where < > is the time mean over the final lastinterval of the
C     run: the meridional volume transport, in Sverdrups, across the
C     SOUTHERN face of grid row jsec = cost_atl_jsec, over the whole
C     row, from the surface over kmax = cost_atl_kmaxdepth levels.
C     Both come from data.cost (cost.h, cost_readparms.F, since
C     2026-10-20; the rows in use are 127 "26 N", 148 "43 N", 175
C     "60 N" and 74 "25 S", named by the row's centre; analyses/
C     DINO_1deg/grid_and_cost_sections.ipynb maps a latitude to a
C     row, and analyses/DINO_1deg/adjoint/kappa_v_ensemble_gmFwd/
C     overturning_maximum.py locates the overturning maximum). With
C     kmax at the interface where the overturning streamfunction
C     peaks on that row, J is the overturning maximum itself.
C
C     With cost_atl_quantity = 'heat' (2026-10-31) the integrand is
C     the product cost_accumulate_mean.F accumulates at the same face,
C     cMeanThetaVVel = < 0.5*(theta(i,j,k)+theta(i,j-1,k)) * vVel >,
C     and the scaling is rhoConst * HeatCapacity_Cp * 1e-15:
C
C       J = mult_atl * rho0 Cp 1e-15 * < sum_i sum_{k<=kmax}
C                 theta_face vVel dxG drF hFacS >        in petawatts,
C
C     the meridional heat transport across the row when kmax = Nr
C     (cost_readparms.F warns when it is less: the upper branch only).
C     theta is in degrees C as the model carries it, so the value is
C     independent of the temperature origin only where the net volume
C     transport across the row vanishes, as it does across a closed
C     basin row up to the surface freshwater flux. rho0 and Cp are
C     rhoConst and HeatCapacity_Cp of PARAMS.h: in DINO rhoConst takes
C     rhoNil = 1035 kg/m3 (input_tap/data) and Cp its default of
C     3994 J/kg/K; STDOUT.0000 prints both.
C
C     The time mean: cost_tile.F calls cost_accumulate_mean.F at
C     every step whose end time lies in the final lastinterval
C     (data.cost; default 30 days), adding vVel*deltaTClock/
C     lastinterval to cMeanVVel, so after a run of at least
C     lastinterval cMeanVVel is the mean over that window. A shorter
C     run accumulates every step, and the sum then covers only the
C     run's length; meanFrac divides that out, so J is the mean over
C     the time actually covered in either case (a 5-day validation
C     run reports the 5-day mean, not one sixth of it).
C
C     Each tile adds the transport through its own part of the row
C     to objf_atl(bi,bj); cost_final.F sums the tiles and the
C     processes, so J is the transport across the whole row and does
C     not depend on the domain decomposition. hFacS is the wet
C     fraction of the face (1 in every cell of every DINO section, so
C     it only masks land here); the free surface is linear, so it is
C     a grid constant.
C
C     Until 2026-10-29 this file kept the tree's form (pkg/cost): at
C     each level it divided each tile's sum by the tile's own count
C     of wet cells, then summed the tiles. Along every DINO row the
C     counts are 16, 17 and 16, so that J was about 1/16.6 of the
C     transport in Sv at 43 N and 60 N but 1/14.8 at 26 N and 1/25 at
C     25 S, where the western boundary current opposes the interior;
C     it depended on the decomposition, and weighted
C     the middle third of the row 6 % less than the rest; a run
C     shorter than lastinterval reported the covered fraction of the
C     mean. A run of that form has no cost_units line in its
C     build_info.txt; a run of this form carries cost_units=Sv. The
C     heat-transport branch of the tree file (the case without
C     ALLOW_COST_ATLANTIC_HEAT_DOMASS: the same per-tile form of the
C     product) and its unused meridional section are gone; the heat
C     transport here is the namelist choice above, whatever
C     COST_OPTIONS.h says about ..._DOMASS.

      meanFrac = MIN( endTime - startTime, lastinterval )
     &         / lastinterval
      doHeat = cost_atl_quantity .EQ. 'heat'

      DO bj=myByLo(myThid),myByHi(myThid)
       DO bi=myBxLo(myThid),myBxHi(myThid)

        tileTransport = 0. _d 0
        DO j=1,sNy
         jg = myYGlobalLo-1+(bj-1)*sNy+j
         IF ( jg .EQ. cost_atl_jsec ) THEN
          IF ( doHeat ) THEN
           DO k=1,cost_atl_kmaxdepth
            DO i=1,sNx
             tileTransport = tileTransport
     &            + cMeanThetaVVel(i,j,k,bi,bj) * dxG(i,j,bi,bj)
     &            * drF(k) * hFacS(i,j,k,bi,bj)
            ENDDO
           ENDDO
          ELSE
           DO k=1,cost_atl_kmaxdepth
            DO i=1,sNx
             tileTransport = tileTransport
     &            + cMeanVVel(i,j,k,bi,bj) * dxG(i,j,bi,bj)
     &            * drF(k) * hFacS(i,j,k,bi,bj)
            ENDDO
           ENDDO
          ENDIF
         ENDIF
        ENDDO

        IF ( doHeat ) THEN
C        in petawatts (1e15 W), as the mean over the covered time
         objf_atl(bi,bj) = tileTransport * rhoConst * HeatCapacity_Cp
     &                   * 1. _d -15 / meanFrac
        ELSE
C        in Sverdrups (1e6 m3/s), as the mean over the covered time
         objf_atl(bi,bj) = tileTransport * 1. _d -6 / meanFrac
        ENDIF

c--   end of bi,bj loop
       ENDDO
      ENDDO

#endif /* ALLOW_COST_ATLANTIC_HEAT */

      end
